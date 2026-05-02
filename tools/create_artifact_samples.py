import pandas as pd
from pathlib import Path

def create_samples(data_dir, output_dir):
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. entities.csv sample
    entities_path = data_dir / "extracted" / "entities.csv"
    if entities_path.exists():
        df = pd.read_csv(entities_path)
        sample = df.head(200)
        # Add 20 per entity type if possible
        for etype in df["entity_type"].unique():
            etype_sample = df[df["entity_type"] == etype].head(20)
            sample = pd.concat([sample, etype_sample]).drop_duplicates()
        sample.to_csv(output_dir / "entities_sample.csv", index=False)
        print("Created entities_sample.csv")
        
    # 2. result_tuples.csv sample
    results_path = data_dir / "extracted" / "result_tuples.csv"
    if results_path.exists():
        df = pd.read_csv(results_path)
        sample = df.head(200)
        sample.to_csv(output_dir / "result_tuples_sample.csv", index=False)
        print("Created result_tuples_sample.csv")
        
    # 3. paper_entity_summary.csv sample
    summary_path = data_dir / "extracted" / "paper_entity_summary.csv"
    if summary_path.exists():
        df = pd.read_csv(summary_path)
        sample = df.head(100)
        sample.to_csv(output_dir / "paper_entity_summary_sample.csv", index=False)
        print("Created paper_entity_summary_sample.csv")
        
    # 4. paper_section_stats.csv sample
    stats_path = data_dir / "extracted" / "paper_section_stats.csv"
    if stats_path.exists():
        df = pd.read_csv(stats_path)
        sample = df.head(100)
        sample.to_csv(output_dir / "paper_section_stats_sample.csv", index=False)
        print("Created paper_section_stats_sample.csv")

if __name__ == "__main__":
    create_samples("Data", "artifacts/samples")
