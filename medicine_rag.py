import os
import re
import json
import uuid
from datetime import datetime
import chromadb
from chromadb.utils import embedding_functions
from ocr_utils import extract_medicine_from_image
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta
from supabase import create_client

# Try to import Gemini
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class MedicineRAG:
    def __init__(self, db_path="./medicine_db"):
        """
        Initialize the Medicine RAG system.
        Args:
            db_path: Path to store the ChromaDB database.
        """
        self.db_path = db_path
        self.table_name = "medicines"
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=db_path)
        # Use default embedding function (sentence-transformers)
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
        # Shared fallback collection for legacy/unscoped usage
        self.collection = self.client.get_or_create_collection(
            name="medicines",
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"}
        )

        if os.getenv("DELETE_LEGACY_SHARED_CHROMA", "false").lower() == "true":
            try:
                self.client.delete_collection("medicines")
            except Exception:
                pass
            self.collection = self.client.get_or_create_collection(
                name="medicines",
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"}
            )
        # Initialize Gemini if available
        self.llm = None
        if GEMINI_AVAILABLE:
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                model_name = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
                self.llm = genai.GenerativeModel(model_name)

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
        self.supabase = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None

    @staticmethod
    def _user_filter(user_id):
        """Build a Chroma metadata filter for a specific user."""
        if not user_id:
            return None
        return {"user_id": str(user_id)}

    def _collection_for_user(self, user_id=None):
        """Return the Chroma collection for a specific user, or the shared fallback collection."""
        if not user_id:
            return self.collection

        safe_user_id = re.sub(r"[^A-Za-z0-9_]", "_", str(user_id))[:48]
        collection_name = f"medicines_{safe_user_id}"
        return self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"}
        )

    def _normalize_name(self, name):
        return (name or "").strip().lower()

    def _medicine_query(self):
        if not self.supabase:
            return None
        return self.supabase.table(self.table_name)

    def _select_user_rows(self, user_id):
        if not self.supabase or not user_id:
            return []
        try:
            response = (
                self._medicine_query()
                .select("*")
                .eq("user_id", str(user_id))
                .order("added_date", desc=True)
                .execute()
            )
            return response.data or []
        except Exception as e:
            if 'PGRST205' in str(e) or 'schema cache' in str(e).lower():
                print("⚠️ Supabase medicines table is missing; using Chroma fallback until the schema is created.")
                return None
            raise

    def _fetch_rows_by_ids(self, medicine_ids, user_id=None):
        if not self.supabase or not medicine_ids:
            return []
        try:
            query = self._medicine_query().select("*").in_("id", medicine_ids)
            if user_id:
                query = query.eq("user_id", str(user_id))
            response = query.execute()
            rows = response.data or []
            row_map = {row["id"]: row for row in rows}
            return [row_map[medicine_id] for medicine_id in medicine_ids if medicine_id in row_map]
        except Exception as e:
            if 'PGRST205' in str(e) or 'schema cache' in str(e).lower():
                return []
            raise

    def _row_to_medicine_payload(self, row):
        if not row:
            return {}
        return {
            "id": row.get("id"),
            "document": row.get("raw_text") or "",
            "metadata": row,
            "days_until_expiry": self._get_expiry_status(row.get("exp_date", ""))[0],
            "expiry_status": self._get_expiry_status(row.get("exp_date", ""))[1],
        }



    # ── Date Utilities ────────────────────────────────────────────────

    @staticmethod
    def _parse_date(date_str):
        """Try to parse a date string in any format using dateutil."""
        if not date_str:
            return None
        try:
            # Normalize 2-digit year at the end of the string to 4-digit year (e.g. JUL.24 -> JUL.2024)
            # This prevents dateutil from confusing YY with DD and defaulting to the current year.
            date_str = re.sub(r'(^|[/.\-\s])(\d{2})$', r'\g<1>20\2', date_str.strip())
            
            # Default to the end of the current month if day is missing (standard for medicines)
            dt = date_parser.parse(date_str.replace('.', '-'))
            if len(date_str) <= 8: # likely just month/year (e.g. 07/2024)
                # push to the last day of that month
                dt = dt + relativedelta(day=31)
            return dt
        except Exception:
            return None

    def _get_expiry_status(self, exp_date_str):
        """Return (days_until_expiry, status_label) for a given expiry date string."""
        exp_date = self._parse_date(exp_date_str)
        if not exp_date:
            return None, "unknown"
        days = (exp_date - datetime.now()).days
        if days < 0:
            return days, "expired"
        elif days <= 30:
            return days, "expiring_soon"
        elif days <= 90:
            return days, "expiring_warning"
        else:
            return days, "ok"

    # ── CRUD Operations ───────────────────────────────────────────────

    def _generate_medicine_id(self, medicine_info):
        """Generate a unique ID for a medicine based on its properties."""
        name_part = medicine_info["name"] or "unknown"
        exp_part = medicine_info["exp_date"] or datetime.now().strftime("%Y%m%d")
        clean_name = re.sub(r'[^\w]', '', name_part)[:20].lower()
        clean_exp = re.sub(r'[^\w]', '', exp_part)
        return f"med_{clean_name}_{clean_exp}"

    def _find_existing_medicine(self, medicine_info, user_id=None):
        """
        Check if a medicine with the same name already exists in the DB.
        Returns the existing ID or None.
        """
        if not medicine_info.get("name"):
            return None
        search_name = self._normalize_name(medicine_info["name"])

        if self.supabase and user_id:
            try:
                rows = self._select_user_rows(user_id)
                if rows is None:
                    return None
                for row in rows:
                    if self._normalize_name(row.get("name")) == search_name:
                        return row.get("id")
                return None
            except Exception:
                return None

        collection = self._collection_for_user(user_id)
        all_meds = collection.get(include=["metadatas"])
        if all_meds and all_meds['metadatas']:
            for i, meta in enumerate(all_meds['metadatas']):
                existing_name = self._normalize_name(meta.get("name"))
                if existing_name and existing_name == search_name:
                    return all_meds['ids'][i]
        return None

    def add_medicine_from_image(self, image_path="image.png", user_id=None):
        """
        Process a medicine image: Gemini Vision extracts info, store in vector DB.
        If the same medicine already exists, it will be updated.
        Returns (medicine_info, expiry_status, is_update).
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        print(f"Processing image: {image_path}")
        # Gemini Vision returns structured dict directly
        medicine_info = extract_medicine_from_image(image_path)

        # Check for existing medicine to update
        existing_id = self._find_existing_medicine(medicine_info, user_id=user_id)
        is_update = existing_id is not None
        med_id = existing_id or str(uuid.uuid4())

        # Build the document text for vector search
        raw_text = medicine_info.get("raw_text") or ""
        other_info = medicine_info.get("other_info") or []
        full_text = f"{medicine_info.get('name', '')} {medicine_info.get('dose', '')} {raw_text} {' '.join(other_info) if isinstance(other_info, list) else other_info}"

        # Standardize dates to MM/YYYY format
        for date_key in ['mfd', 'exp_date']:
            val = medicine_info.get(date_key)
            if val:
                parsed = self._parse_date(val)
                if parsed:
                    medicine_info[date_key] = parsed.strftime('%m/%Y')

        # Prepare metadata (ChromaDB requires string values)
        metadata = {
            "name": medicine_info.get("name") or "",
            "mfd": medicine_info.get("mfd") or "",
            "exp_date": medicine_info.get("exp_date") or "",
            "dose": medicine_info.get("dose") or "",
            "batch_no": medicine_info.get("batch_no") or "",
            "manufacturer": medicine_info.get("manufacturer") or "",
            "added_date": datetime.now().isoformat(),
            "image_path": image_path,
            "user_id": str(user_id or ""),
            "medicine_id": med_id,
        }

        if self.supabase and user_id:
            row_payload = {
                "id": med_id,
                "user_id": str(user_id),
                "name": metadata["name"],
                "mfd": metadata["mfd"],
                "exp_date": metadata["exp_date"],
                "dose": metadata["dose"],
                "batch_no": metadata["batch_no"],
                "manufacturer": metadata["manufacturer"],
                "raw_text": medicine_info.get("raw_text") or "",
                "other_info": json.dumps(other_info) if isinstance(other_info, list) else str(other_info or ""),
                "image_path": image_path,
                "added_date": metadata["added_date"],
                "updated_at": metadata["added_date"],
            }

            try:
                if is_update:
                    self._medicine_query().update(row_payload).eq("id", med_id).eq("user_id", str(user_id)).execute()
                else:
                    self._medicine_query().insert(row_payload).execute()
            except Exception as e:
                if 'PGRST205' in str(e) or 'schema cache' in str(e).lower():
                    print("⚠️ Supabase medicines table not found. Storing medicine in Chroma fallback only until the table is created.")
                else:
                    raise
        else:
            print("⚠️ Supabase not configured; using Chroma-only storage for this medicine.")

        collection = self._collection_for_user(user_id)
        if is_update:
            collection.delete(ids=[med_id])

        collection.add(
            documents=[full_text],
            metadatas=[metadata],
            ids=[med_id]
        )

        # Compute expiry status
        days, status = self._get_expiry_status(medicine_info.get("exp_date"))
        expiry_info = {"days": days, "status": status}

        action = "updated" if is_update else "added"
        print(f"✅ Medicine {action}: {medicine_info.get('name') or 'Unknown'}")
        return medicine_info, expiry_info, is_update

    def delete_medicine(self, med_id, user_id=None):
        """Delete a medicine by its ID."""
        if self.supabase and user_id:
            try:
                self._medicine_query().delete().eq("id", med_id).eq("user_id", str(user_id)).execute()
            except Exception as e:
                if 'PGRST205' in str(e) or 'schema cache' in str(e).lower():
                    print("⚠️ Supabase medicines table is missing; deleting from Chroma fallback only.")
                else:
                    raise
        collection = self._collection_for_user(user_id)
        collection.delete(ids=[med_id])

    # ── Query & RAG ───────────────────────────────────────────────────

    def query_medicines(self, question, n_results=5, user_id=None):
        """
        Query the medicine database using vector similarity.
        Returns a list of matching medicines.
        """
        collection = self._collection_for_user(user_id)
        count = collection.count()
        if count == 0:
            return []
        n = min(n_results, count)
        results = collection.query(
            query_texts=[question],
            n_results=n,
            include=["documents", "metadatas", "distances"]
        )

        medicines = []
        if results['documents'] and results['documents'][0]:
            result_ids = results.get('ids', [[]])[0]
            rows = self._fetch_rows_by_ids(result_ids, user_id=user_id)
            row_map = {row.get("id"): row for row in rows}
            for i, doc in enumerate(results['documents'][0]):
                med_id = result_ids[i] if i < len(result_ids) else None
                row = row_map.get(med_id)
                medicines.append({
                    "document": row.get("raw_text") if row else doc,
                    "metadata": row or results['metadatas'][0][i],
                    "distance": results['distances'][0][i] if 'distances' in results else None,
                })
        return medicines

    def ask(self, question, n_results=5, user_id=None):
        """
        RAG-powered question answering.
        Retrieves relevant medicines, then uses Gemini to generate a natural-language answer.
        Falls back to raw results if Gemini is unavailable.
        """
        medicines = self.query_medicines(question, n_results, user_id=user_id)
        if not medicines:
            return {
                "answer": "No medicines found in your inventory. Please upload a medicine image first.",
                "sources": []
            }

        # Build context from retrieved documents
        context_parts = []
        for i, med in enumerate(medicines, 1):
            meta = med["metadata"]
            days, status = self._get_expiry_status(meta.get("exp_date"))
            status_text = f"({status}, {days} days)" if days is not None else "(expiry unknown)"
            context_parts.append(
                f"Medicine {i}:\n"
                f"  Name: {meta.get('name', 'Unknown')}\n"
                f"  Dose: {meta.get('dose', 'N/A')}\n"
                f"  MFD: {meta.get('mfd', 'N/A')}\n"
                f"  Expiry: {meta.get('exp_date', 'N/A')} {status_text}\n"
                f"  Batch: {meta.get('batch_no', 'N/A')}\n"
                f"  Manufacturer: {meta.get('manufacturer', 'N/A')}\n"
                f"  Raw OCR Text: {med['document'][:200]}"
            )
        context = "\n\n".join(context_parts)

        # Generate answer using Gemini
        if self.llm:
            prompt = (
                "You are MedAsis, an AI-powered personal medicine assistant. \n"
                "The user will ask questions about their medicine inventory or general medicine queries.\n\n"
                f"CURRENT DATE: {datetime.now().strftime('%Y-%m-%d')}\n\n"
                "IMPORTANT RULES:\n"
                "- If the user asks if they have a medicine or about its expiry, answer strictly using the MEDICINE INVENTORY data below.\n"
                "- If the user asks about the uses, side effects, or general information of a medicine, you MAY use your general medical knowledge to explain it, but clearly state that this is general information and not professional medical advice.\n"
                "- If a medicine in their inventory is expired or expiring soon, prominently warn them.\n"
                "- Be concise, helpful, and format your output beautifully with Markdown (bullet points, bold text).\n\n"
                f"=== MEDICINE INVENTORY ===\n{context}\n\n"
                f"=== USER QUESTION ===\n{question}\n\n"
                "Answer:"
            )
            try:
                response = self.llm.generate_content(prompt)
                answer = response.text
            except Exception as e:
                answer = f"LLM error: {e}\n\nHere are the matching medicines:\n{context}"
        else:
            answer = f"(LLM not configured — showing raw results)\n\n{context}"

        sources = [
            {
                "name": med["metadata"].get("name", "Unknown"),
                "exp_date": med["metadata"].get("exp_date", ""),
                "dose": med["metadata"].get("dose", ""),
            }
            for med in medicines
        ]

        return {"answer": answer, "sources": sources}

    # ── Expiry Checks ─────────────────────────────────────────────────

    def get_expiring_medicines(self, days_threshold=30, user_id=None):
        """Get medicines expiring within the specified number of days."""
        if self.supabase and user_id:
            rows = self._select_user_rows(user_id)
            if rows is not None:
                all_medicines = {"data": rows}
            else:
                collection = self._collection_for_user(user_id)
                all_medicines = collection.get(include=["metadatas", "documents"])
        else:
            collection = self._collection_for_user(user_id)
            all_medicines = collection.get(include=["metadatas", "documents"])
        expiring = []

        rows = all_medicines.get("data") if isinstance(all_medicines, dict) and "data" in all_medicines else None
        if rows is not None:
            for row in rows:
                exp_date_str = row.get('exp_date', '')
                days, status = self._get_expiry_status(exp_date_str)
                if days is not None and 0 <= days <= days_threshold:
                    expiring.append({
                        "id": row.get("id"),
                        "document": row.get("raw_text") or "",
                        "metadata": row,
                        "days_until_expiry": days,
                        "status": status,
                    })
        elif all_medicines['metadatas']:
            for i, metadata in enumerate(all_medicines['metadatas']):
                exp_date_str = metadata.get('exp_date', '')
                days, status = self._get_expiry_status(exp_date_str)
                if days is not None and 0 <= days <= days_threshold:
                    expiring.append({
                        "id": all_medicines['ids'][i],
                        "document": all_medicines['documents'][i],
                        "metadata": metadata,
                        "days_until_expiry": days,
                        "status": status,
                    })

        expiring.sort(key=lambda x: x['days_until_expiry'])
        return expiring

    def get_expired_medicines(self, user_id=None):
        """Get medicines that have already expired."""
        if self.supabase and user_id:
            rows = self._select_user_rows(user_id)
            if rows is not None:
                all_medicines = {"data": rows}
            else:
                collection = self._collection_for_user(user_id)
                all_medicines = collection.get(include=["metadatas", "documents"])
        else:
            collection = self._collection_for_user(user_id)
            all_medicines = collection.get(include=["metadatas", "documents"])
        expired = []

        rows = all_medicines.get("data") if isinstance(all_medicines, dict) and "data" in all_medicines else None
        if rows is not None:
            for row in rows:
                exp_date_str = row.get('exp_date', '')
                days, status = self._get_expiry_status(exp_date_str)
                if days is not None and days < 0:
                    expired.append({
                        "id": row.get("id"),
                        "document": row.get("raw_text") or "",
                        "metadata": row,
                        "days_expired": abs(days),
                        "status": "expired",
                    })
        elif all_medicines['metadatas']:
            for i, metadata in enumerate(all_medicines['metadatas']):
                exp_date_str = metadata.get('exp_date', '')
                days, status = self._get_expiry_status(exp_date_str)
                if days is not None and days < 0:
                    expired.append({
                        "id": all_medicines['ids'][i],
                        "document": all_medicines['documents'][i],
                        "metadata": metadata,
                        "days_expired": abs(days),
                        "status": "expired",
                    })

        expired.sort(key=lambda x: x['days_expired'])
        return expired

    def list_all_medicines(self, user_id=None):
        """List all medicines in the database with expiry status."""
        if self.supabase and user_id:
            rows = self._select_user_rows(user_id)
            if rows is not None:
                medicines = []
                for row in rows:
                    days, status = self._get_expiry_status(row.get('exp_date', ''))
                    medicines.append({
                        "id": row.get("id"),
                        "document": row.get("raw_text") or "",
                        "metadata": row,
                        "days_until_expiry": days,
                        "expiry_status": status,
                    })
                return medicines

        collection = self._collection_for_user(user_id)
        results = collection.get(include=["metadatas", "documents"])
        medicines = []
        if results['metadatas']:
            for i, metadata in enumerate(results['metadatas']):
                days, status = self._get_expiry_status(metadata.get('exp_date', ''))
                medicines.append({
                    "id": results['ids'][i],
                    "document": results['documents'][i],
                    "metadata": metadata,
                    "days_until_expiry": days,
                    "expiry_status": status,
                })
        return medicines


# ── CLI usage ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    rag = MedicineRAG()

    # Add medicine from image
    try:
        medicine_info, expiry_info, is_update = rag.add_medicine_from_image()
        print("\nExtracted Medicine Info:")
        for key, value in medicine_info.items():
            if key != "raw_text":
                print(f"  {key}: {value}")
        print(f"\nExpiry Status: {expiry_info['status']} ({expiry_info['days']} days)")
    except Exception as e:
        print(f"Error processing image: {e}")

    # Example query
    print("\n--- RAG Query ---")
    result = rag.ask("What medicines do I have?")
    print(result["answer"])

    # Check for expiring medicines
    print("\n--- Expiring Medicines (next 30 days) ---")
    expiring = rag.get_expiring_medicines(30)
    if expiring:
        for med in expiring:
            print(f"  ⚠️ {med['metadata'].get('name', 'Unknown')} expires in {med['days_until_expiry']} days")
    else:
        print("  No medicines expiring in the next 30 days.")