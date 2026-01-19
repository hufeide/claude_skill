# Document Summary Schema

This schema defines the **structured output format** for all document summaries
persisted via the `save_summary_to_db` MCP tool.

The goal is **consistency, comparability, and long-term reuse**.

---

## 🔑 Required Fields (Must Always Be Present)

- **document_id**: string  
  Unique identifier for the document (e.g. hash or filename-based).

- **filename**: string  
  Original file name of the document.

- **status**: `completed` | `failed`  
  Processing result.

- **executive_summary**: string  
  A concise, information-dense summary based strictly on the document content.

---

## 🧠 Core Analytical Fields (Required if status = completed)

- **domain**:  
  One of: `macro`, `micro`, `finance`, `political-economy`, `other`

- **key_arguments**:  
  List of the main claims or conclusions made in the document.

- **key_models_or_frameworks** (optional if none present):
  - name  
  - description

- **key_variables_or_concepts** (optional):
  - term  
  - explanation

---

## ⚠️ Failure Handling (Required if status = failed)

- **failure_reason**: string  
  Short explanation of why the document could not be processed.

---

## 📝 Notes

- Do not hallucinate missing information.
- If a field is not applicable, omit it instead of inventing content.
- Every processed document must conform to this schema before being persisted.