# Day 9 Corpus Expansion Policy

## Context
The previous corpus manifest (Day 8) contained 100 papers, but only 72 were successfully parsed and included in the executable indices. The remaining 28 papers were either 403-blocked by publishers, returned invalid PDFs, or were otherwise inaccessible to the automated download script.

To meet the requirement of a **100-paper executable corpus**, we are expanding the candidate pool and replacing inaccessible papers with high-quality, open-access alternatives.

## Objectives
1.  Reach exactly **100 parsed and indexed papers** in the `Data_v2` bundle.
2.  Maintain strict topical relevance to AIGC (AI-Generated Content) detection and image forensics.
3.  Prioritize papers with accessible PDF URLs (e.g., arXiv, OpenAccess CVF).

## Selection Criteria for Replacements

### 1. Topic Inclusion (Mandatory)
*   **Core**: AI-generated image detection, GAN/Diffusion forgery detection, deepfake forensics.
*   **Secondary**: Benchmark datasets for AIGC forensics, model watermarking, semantic consistency checks.
*   **Excluded**: Medical-only imaging, audio-only forensics, generic computer vision (e.g., standard object detection), non-image-forensics video work (unless image-frame relevant).

### 2. Accessibility (Mandatory for Executable Corpus)
*   Must have a direct PDF URL or a reliable open-access landing page.
*   Prefer arXiv (`arxiv.org`), CVF (`openaccess.thecvf.com`), or OpenReview.
*   Avoid paywalled publishers (Nature, Science, IEEE Xplore without institutional bypass) for the **reproducible** corpus bundle.

### 3. Ranking Priority
*   **Citation Count**: Higher citation rank within the AIGC niche.
*   **Recency**: Favor papers from 2023-2025 to capture current diffusion model forensics.
*   **Benchmark/Model Relevance**: Papers introducing or building on major benchmarks (GenImage, ArtiFact, FaceForensics++).

## Diversity Controls
*   **Face Forensics Cap**: Limit the number of pure "Face Swap" papers to ensure diversity across general AIGC (landscapes, objects, textures).
*   **Survey Papers**: Maximum of 5-8 comprehensive surveys to ensure the bulk of the corpus is empirical/methodological.
*   **Publisher Diversity**: Avoid over-reliance on a single lab or venue.

## Documentation of Failures
Any paper from the original manifest that remains inaccessible will be documented in `Data_v2/download_logs/download_report.md` with specific error codes (e.g., 403 Forbidden, 404 Not Found) to maintain transparency about the original selection vs. the executable reality.

## Deliverables
*   `corpus/manifest_executable_100.csv`: The final target list for Day 9.
*   `Data_v2/`: The new runtime bundle containing 100 parsed papers.
*   `docs/day9_corpus_expansion_report.md`: Audit of the 28 replacements made.
