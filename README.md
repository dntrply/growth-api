# WHO Growth API

A FastAPI-based API for calculating child growth metrics based on World Health Organization (WHO) growth standards.

## Overview

This API allows healthcare professionals, researchers, and developers to calculate z-scores and classifications for common child growth parameters:

- Length/height-for-age
- Weight-for-age
- Weight-for-length

The calculations use the WHO's LMS method and reference tables for accurate standardization.

## Features

- Calculate z-scores for children's growth measurements
- Classify growth status based on WHO standards
- Handles both boys and girls data
- Supports age-based and length-based calculations

## Available Growth Indicators

| Indicator | Description | Required Parameters |
|-----------|-------------|---------------------|
| length    | Length-for-age | sex, years, months, length |
| weight    | Weight-for-age | sex, years, months, weight |
| wfl       | Weight-for-length | sex, length, weight |

## Installation

1. Clone the repository
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Start the API server:

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.

### API Endpoints

#### POST /zscore

Calculate the z-score and classification for a child's growth measurement.

**Request Body:**

```json
{
  "sex": "M",          // "M" for male, "F" for female
  "indicator": "weight", // "length", "weight", or "wfl"
  "years": 2,          // Age in completed years (for length & weight)
  "months": 6,         // Additional months (for length & weight)
  "length": 85.5,      // Length in cm (required for "length" or "wfl")
  "weight": 12.3       // Weight in kg (required for "weight" or "wfl")
}
```

**Response:**

```json
{
  "z_score": 0.5,
  "classification": "Normal"
}
```

## Classification Ranges

### Length/Height-for-age
- < -3: Severely stunted
- -3 to < -2: Moderately stunted
- -2 to ≤ 2: Normal
- > 2: Tall

### Weight-for-age
- < -3: Severe underweight
- -3 to < -2: Underweight
- -2 to ≤ 2: Normal
- > 2: Overweight

### Weight-for-length
- < -3: Severe wasting
- -3 to < -2: Wasting
- -2 to ≤ 2: Normal
- > 2: Overweight

## Data Source

The API uses WHO child growth standard reference tables, which are included in the `data/` directory:
- WHO-Boys-Length-for-age-Percentiles_LMS.csv
- WHO-Boys-Weight-for-age-Percentiles_LMS.csv
- WHO-Boys-Weight-for-length-Percentiles_LMS.csv
- WHO-Girls-Weight-for-age-Percentiles_LMS.csv
- WHO-Girls-Weight-for-length-Percentiles_LMS.csv

## Dependencies

- FastAPI - Web framework for building APIs
- Pydantic - Data validation and settings management
- Pandas - Data manipulation and analysis
- Uvicorn - ASGI server implementation

## License

[Add your preferred license here]

## Contributing

[Add your contribution guidelines here]

## TODO

- Extend support for children beyond 2 years of age using WHO standards
  - Reference: https://www.who.int/tools/child-growth-standards/standards/length-height-for-age
- Add BMI-for-age calculations
- Implement percentile calculations in addition to z-scores
- Add interactive API documentation with Swagger UI
- Create Docker container for easy deployment
