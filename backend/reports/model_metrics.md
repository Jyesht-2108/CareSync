# CareSync — Model Metrics Report (Enhanced with MIMIC-III)
**Date**: Auto-generated during training
**Datasets**: 
  - Original: 50 patients, 24h hourly vitals, demographics, EHR notes
  - MIMIC-III: 4,240 ICU patients with vitals, demographics, 30-day mortality
  - **Total**: 4290 patients
**Label distribution**: {'Low': 1700, 'Medium': 1487, 'High': 1103}
**Evaluation**: Stratified 5-Fold Cross-Validation
**Class balancing**: class_weight='balanced' (LR, RF) / sample_weight (XGB)

## Model Comparison

| Model | ROC-AUC (weighted) | High-Risk Recall |
|-------|-------------------|------------------|
| Logistic Regression ✅ | 0.9415 | 0.5839 |
| Random Forest | 0.9446 | 0.5449 |
| XGBoost | 0.9452 | 0.5802 |

**Selected model**: Logistic Regression

## Classification Report (Best Model — CV)

```
              precision    recall  f1-score   support

         Low       0.90      0.98      0.94      1700
      Medium       0.83      0.95      0.89      1487
        High       0.88      0.58      0.70      1103

    accuracy                           0.87      4290
   macro avg       0.87      0.84      0.84      4290
weighted avg       0.87      0.87      0.86      4290
```

## Confusion Matrix (Best Model — CV)

```
              Predicted
              Low  Med  High
  Actual Low   1666    6   28
  Actual Med     8  1418   61
  Actual High  176  283  644
```

## Top 15 Feature Importances

| Rank | Feature | Importance |
|------|---------|------------|
| 1 | tfidf_organ | 2.2491 |
| 2 | tfidf_infection moderate | 2.0409 |
| 3 | tfidf_dysfunction | 2.0089 |
| 4 | tfidf_moderate | 2.0089 |
| 5 | tfidf_moderate organ | 2.0089 |
| 6 | tfidf_organ dysfunction | 2.0089 |
| 7 | tfidf_failure | 1.3442 |
| 8 | tfidf_organ failure | 1.3442 |
| 9 | tfidf_severe | 1.3442 |
| 10 | tfidf_severe organ | 1.3442 |
| 11 | tfidf_ventilation moderate | 1.1618 |
| 12 | tfidf_diabetes moderate | 0.9838 |
| 13 | tfidf_present moderate | 0.9404 |
| 14 | tfidf_infection severe | 0.9055 |
| 15 | tfidf_diabetes | 0.7873 |

## Notes

- All evaluation uses out-of-fold predictions (no data leakage).
- Class weighting ensures the model penalizes missing High-risk patients.
- MIMIC-III 30-day mortality was mapped to High risk; SOFA scores used for Medium/Low stratification.
- Combined dataset provides significantly larger training set (4,290 patients vs original 50).
- Feature importances are from the full-data retrained model.
