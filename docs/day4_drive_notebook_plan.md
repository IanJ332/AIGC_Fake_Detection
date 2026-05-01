# Day 4: Cloud Data Orchestration Plan

## Goal
Establish a robust, reproducible cloud-based data acquisition and parsing environment using Google Colab and Google Drive. This ensures that the Research Comprehension System can handle a 100-paper corpus with high document coverage without being limited by local machine resources or Git storage constraints.

## Strategic Shift: Google Drive as Primary Store
- **Persistence**: All large assets (PDFs, parsed JSON, extracted sections) will live exclusively in Google Drive.
- **Temporary Compute**: Google Colab provides the runtime. The GitHub repository is cloned temporarily to provide the scripts but does not store binary data.
- **Fallback Recovery**: Implementation of a secondary acquisition layer to recover papers that failed direct download due to publisher-level bot protection.

## Implementation Workflow (Notebook 01)
1. **Environment Setup**: Mount Drive, create standardized folder hierarchy, and detect runtime capabilities.
2. **Repository Sync**: Clone the fresh codebase and establish symlinks from the repo `corpus/` folder to Drive to ensure standard scripts work transparently.
3. **Tiered Acquisition**:
   - **Tier 1 (Direct)**: Execute `download_documents.py` to fetch from known PDF URLs.
   - **Tier 2 (Heuristic Fallback)**: Normalize arXiv links and retry failed downloads.
   - **Tier 3 (Discovery Fallback)**: Query Semantic Scholar and Unpaywall APIs for alternative Open Access sources.
4. **Parsing Gate**: Enforce a minimum threshold of 70 valid PDFs before proceeding to structured parsing.
5. **Evidence Extraction**: Execute the Day 3 parsing pipeline to generate section-level JSON and table candidates.
6. **Readiness Probe**: Generate a `drive_data_status.json` file to communicate project state to subsequent notebooks.

## Implementation Workflow (Notebook 02)
1. **Sampling**: Select a diverse batch of 8 papers (P001-P010) for focused validation.
2. **Quality Audit**: Verify that the PyMuPDF parsing successfully captured essential sections (Abstract, Method, Results).
3. **Entity Extraction**: Run rule-based scanners for Datasets (e.g., GenImage), Models (e.g., DINOv2), and Generators (e.g., Diffusion).
4. **Tuple Probing**: Test result extraction from table candidates, linking metrics to numeric values.
5. **Question Routing**: Validate a multi-type question classifier against 12 test queries.

## Success Criteria
- **Document Coverage**: At least 80 PDFs successfully acquired and registered.
- **Parse Quality**: At least 65 papers successfully parsed into sections.
- **Extraction Yield**: Notebook 02 must find >20 entities in the sample batch.
- **Traceability**: Every document must have a valid SHA256 and mapped metadata in the persistent registry.

## Next Phase
Once Notebook 01 reports `READY_FOR_NOTEBOOK_02`, we will proceed to small-batch claim extraction and evidence anchoring using LLM-assisted probes.
