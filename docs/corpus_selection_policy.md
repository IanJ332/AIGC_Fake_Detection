# Corpus Selection Policy

This document outlines the inclusion/exclusion criteria and scoring methodology for the Research Comprehension System.

## Topic Boundary

### Inclusion Criteria
- Primary topic: AI-generated image detection and image forensics.
- AI-generated image detection, synthetic image detection, diffusion-generated image detection, GAN image detection, deepfake image detection.
- Image forgery detection/localization.
- Robust in-the-wild AIGC detection.
- Benchmark/dataset papers for these areas.

### Exclusion Criteria
- Video-only deepfake detection.
- Audio-only detection.
- Text AI detection.
- Watermark-only generation papers (without detection focus).
- Pure image generation papers without detection/forensics evaluation.

## Scoring Methodology

Each paper is scored on a scale of 0.0 to 1.0 using the following weights:

| Weight | Component | Description |
| :--- | :--- | :--- |
| 0.45 | Citation Count | Normalized citation count (capped for Day 1). |
| 0.25 | Topical Relevance | Keyword matching in title and abstract. |
| 0.15 | PDF Availability | Bonus for papers with a direct PDF URL or Open Access. |
| 0.10 | Benchmark/Dataset | Priority for papers introducing new benchmarks or datasets. |
| 0.05 | Recency Bonus | Bonus for papers published in 2021-2023+. |

## Paper Roles
- **Survey**: Overview of the field.
- **Method**: New detection or forensic techniques.
- **Dataset/Benchmark**: New data for evaluation.
- **Challenge**: Competition or evaluation platform.
