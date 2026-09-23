import pandas as pd
import numpy as np
from pathlib import Path

np.random.seed(42)

crops = {
    "rice": {"N": (80, 100), "P": (35, 60), "K": (35, 50),
             "temp": (20, 30), "humidity": (75, 90),
             "ph": (5.5, 7.5), "rainfall": (200, 300)},
    
    "maize": {"N": (50, 80), "P": (30, 50), "K": (30, 50),
              "temp": (22, 32), "humidity": (50, 70),
              "ph": (5.5, 7.5), "rainfall": (100, 200)},
    
    "chickpea": {"N": (20, 50), "P": (40, 70), "K": (40, 60),
                 "temp": (18, 28), "humidity": (50, 65),
                 "ph": (6.0, 8.0), "rainfall": (60, 120)},
    
    "coffee": {"N": (20, 40), "P": (30, 50), "K": (25, 45),
               "temp": (18, 26), "humidity": (50, 70),
               "ph": (5.5, 6.5), "rainfall": (60, 120)},
    
    "wheat": {"N": (40, 60), "P": (40, 60), "K": (45, 60),
              "temp": (15, 25), "humidity": (60, 75),
              "ph": (6.0, 7.5), "rainfall": (100, 180)},

    "cotton": {"N": (40, 80), "P": (20, 50), "K": (30, 60),
               "temp": (25, 35), "humidity": (50, 70),
               "ph": (5.5, 8.0), "rainfall": (50, 120)},

    "sugarcane": {"N": (80, 140), "P": (40, 80), "K": (60, 120),
                  "temp": (20, 35), "humidity": (60, 85),
                  "ph": (6.0, 8.0), "rainfall": (150, 300)},

    "soybean": {"N": (20, 50), "P": (30, 60), "K": (30, 60),
                "temp": (20, 30), "humidity": (55, 75),
                "ph": (6.0, 7.5), "rainfall": (250, 450)}
}

rows_per_crop = 100
data = []

for crop, ranges in crops.items():
    for _ in range(rows_per_crop):
        N = np.random.uniform(*ranges["N"])
        P = np.random.uniform(*ranges["P"])
        K = np.random.uniform(*ranges["K"])
        temp = np.random.uniform(*ranges["temp"])
        humidity = np.random.uniform(*ranges["humidity"])
        ph = np.random.uniform(*ranges["ph"])
        rainfall = np.random.uniform(*ranges["rainfall"])

        # Irrigation estimation logic (domain-based heuristic)
        irrigation_requirement = max(
            0,
            round((temp * 0.3 + rainfall * 0.02 - humidity * 0.1), 2)
        )

        data.append([
            round(N, 2), round(P, 2), round(K, 2),
            round(temp, 2), round(humidity, 2),
            round(ph, 2), round(rainfall, 2),
            crop, irrigation_requirement
        ])

columns = [
    "N", "P", "K",
    "temperature", "humidity",
    "ph", "rainfall",
    "label", "irrigation_requirement"
]

df = pd.DataFrame(data, columns=columns)
output_path = Path(__file__).with_name("crop_data.csv")
df.to_csv(output_path, index=False)

print(f"Dataset generated successfully: {output_path}")
print("Total rows:", len(df))
