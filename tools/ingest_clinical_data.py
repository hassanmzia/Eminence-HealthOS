#!/usr/bin/env python3
"""
Eminence HealthOS — CLI tool to seed the Qdrant vector store with sample
clinical data for development and testing.

Usage:
    python -m tools.ingest_clinical_data
    python -m tools.ingest_clinical_data --collection clinical_guidelines
    python -m tools.ingest_clinical_data --reset --qdrant-url http://localhost:6333
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Any

# ═══════════════════════════════════════════════════════════════════════════════
# Sample Clinical Guidelines (~20)
# ═══════════════════════════════════════════════════════════════════════════════

SAMPLE_CLINICAL_GUIDELINES: list[str] = [
    # 1
    (
        "Hypertension Management — JNC-8 Guidelines\n\n"
        "For adults aged 60 and older, initiate pharmacologic treatment to lower blood pressure "
        "at systolic BP >= 150 mmHg or diastolic BP >= 90 mmHg, with a target of SBP < 150 and "
        "DBP < 90. For adults aged 18-59, the threshold and goal is 140/90 mmHg. Initial therapy "
        "options include thiazide-type diuretics, ACE inhibitors, ARBs, or calcium channel blockers. "
        "For Black patients without CKD, initial therapy should be a thiazide-type diuretic or CCB. "
        "For patients with CKD regardless of race, initial therapy should include an ACE inhibitor "
        "or ARB. ICD-10: I10 (Essential hypertension), I11 (Hypertensive heart disease)."
    ),
    # 2
    (
        "Type 2 Diabetes Management — ADA Standards of Care 2024\n\n"
        "Target HbA1c < 7% for most non-pregnant adults; individualize to < 6.5% or < 8% based on "
        "patient factors. Metformin remains first-line pharmacotherapy. For patients with established "
        "ASCVD, heart failure, or CKD, add SGLT2 inhibitor or GLP-1 receptor agonist with proven "
        "cardiovascular benefit regardless of HbA1c. Monitor HbA1c every 3 months until stable, "
        "then every 6 months. Screen for diabetic retinopathy annually, nephropathy (uACR + eGFR) "
        "annually, and neuropathy at diagnosis and then annually. ICD-10: E11 (Type 2 diabetes)."
    ),
    # 3
    (
        "Heart Failure Management — ACC/AHA Guidelines\n\n"
        "For HFrEF (LVEF <= 40%), initiate guideline-directed medical therapy (GDMT): ACE inhibitor "
        "or ARB (or ARNI), beta-blocker (carvedilol, metoprolol succinate, or bisoprolol), "
        "mineralocorticoid receptor antagonist (spironolactone or eplerenone), and SGLT2 inhibitor. "
        "Titrate to maximum tolerated doses. Add hydralazine-isosorbide dinitrate in Black patients "
        "with persistent symptoms. Consider ICD for primary prevention if LVEF <= 35% despite 3 "
        "months of optimal therapy. For HFpEF (LVEF > 50%), SGLT2 inhibitors are recommended. "
        "ICD-10: I50.2 (Systolic heart failure), I50.3 (Diastolic heart failure)."
    ),
    # 4
    (
        "Asthma Management — GINA 2024 Guidelines\n\n"
        "Step 1-2 (mild): Low-dose ICS-formoterol as needed (preferred) or low-dose ICS whenever "
        "SABA is used. Step 3 (moderate): Low-dose ICS-formoterol maintenance and reliever. "
        "Step 4: Medium-dose ICS-formoterol maintenance and reliever. Step 5 (severe): Add LAMA "
        "or refer for biologic therapy (anti-IgE, anti-IL5, anti-IL4R). Assess asthma control at "
        "every visit using ACT score. Before stepping up, check inhaler technique, adherence, and "
        "comorbidities. ICD-10: J45 (Asthma)."
    ),
    # 5
    (
        "COPD Management — GOLD 2024 Report\n\n"
        "Group A (few symptoms, low risk): short-acting bronchodilator PRN. Group B (more symptoms): "
        "LABA or LAMA. Group E (exacerbation history): LABA+LAMA; if eosinophils >= 300, consider "
        "LABA+LAMA+ICS triple therapy. Smoking cessation is the single most effective intervention. "
        "Pulmonary rehabilitation recommended for all symptomatic patients. Annual influenza and "
        "pneumococcal vaccines are essential. ICD-10: J44 (COPD)."
    ),
    # 6
    (
        "Atrial Fibrillation Management — AHA/ACC/HRS Guidelines\n\n"
        "Assess stroke risk with CHA2DS2-VASc score. Anticoagulation recommended for score >= 2 in "
        "men and >= 3 in women. DOACs (apixaban, rivaroxaban, dabigatran, edoxaban) preferred over "
        "warfarin for non-valvular AF. Rate control target: resting HR < 110 bpm (lenient) or "
        "< 80 bpm (strict) based on symptoms. First-line rate control: beta-blockers or "
        "non-dihydropyridine CCBs. Rhythm control with catheter ablation is recommended for "
        "symptomatic AF failing antiarrhythmic drug therapy. ICD-10: I48 (Atrial fibrillation)."
    ),
    # 7
    (
        "Acute Coronary Syndrome — STEMI Protocol\n\n"
        "Door-to-balloon time target: < 90 minutes for primary PCI. Administer aspirin 325 mg "
        "immediately, P2Y12 inhibitor (ticagrelor or prasugrel preferred over clopidogrel), "
        "anticoagulation with unfractionated heparin. If PCI not available within 120 minutes, "
        "administer fibrinolytic therapy within 30 minutes. Post-PCI: dual antiplatelet therapy "
        "for 12 months, high-intensity statin, beta-blocker, ACE inhibitor. "
        "ICD-10: I21 (Acute myocardial infarction)."
    ),
    # 8
    (
        "Chronic Kidney Disease — KDIGO Guidelines\n\n"
        "Stage CKD by eGFR and albuminuria: G1 (>=90), G2 (60-89), G3a (45-59), G3b (30-44), "
        "G4 (15-29), G5 (<15). Target BP < 120 mmHg systolic with RAAS inhibitor (ACEi or ARB) "
        "for diabetic and proteinuric CKD. Add SGLT2 inhibitor for CKD with eGFR >= 20 and "
        "albuminuria. Avoid NSAIDs, adjust renally-cleared medications. Refer to nephrology at "
        "eGFR < 30 or rapidly declining function. ICD-10: N18 (Chronic kidney disease)."
    ),
    # 9
    (
        "Depression Screening and Management — USPSTF / APA Guidelines\n\n"
        "Screen all adults with PHQ-2; if positive, follow up with PHQ-9. Mild depression (PHQ-9 "
        "5-9): watchful waiting, psychotherapy, or lifestyle modifications. Moderate-severe (PHQ-9 "
        ">= 10): initiate SSRI (sertraline, escitalopram first-line) or SNRI. Reassess at 4-6 "
        "weeks. If inadequate response, optimize dose, switch medication, or augment. CBT is "
        "effective as monotherapy or adjunct. Screen for suicidal ideation at every visit. "
        "ICD-10: F32 (Major depressive disorder, single episode), F33 (Recurrent depressive disorder)."
    ),
    # 10
    (
        "Anticoagulation Management — Warfarin Dosing Protocol\n\n"
        "Target INR 2.0-3.0 for most indications (AF, DVT/PE). Target INR 2.5-3.5 for mechanical "
        "heart valves. Initiate warfarin 5 mg daily for most patients; use 2.5 mg for elderly, "
        "low body weight, liver disease, or concurrent interacting drugs. Check INR daily during "
        "initiation, then weekly, then monthly once stable. Major drug interactions: amiodarone "
        "(reduce dose 30-50%), fluconazole, metronidazole, TMP-SMX (increase INR). "
        "ICD-10: Z79.01 (Long-term anticoagulant use)."
    ),
    # 11
    (
        "Telehealth Visit Protocol — Pre-Visit Assessment\n\n"
        "Before each telehealth encounter, confirm patient identity using two identifiers. "
        "Verify the patient's physical location for jurisdictional compliance. Assess technology "
        "readiness and have a backup phone number. Review current medications, allergies, and "
        "recent vital signs (home BP, glucose, weight). Document informed consent for telehealth "
        "services. Ensure the visit is conducted in a private, HIPAA-compliant setting on both ends."
    ),
    # 12
    (
        "Hyperlipidemia Management — ACC/AHA Cholesterol Guidelines\n\n"
        "For secondary prevention (clinical ASCVD): high-intensity statin (atorvastatin 40-80 mg "
        "or rosuvastatin 20-40 mg). If LDL-C remains >= 70 mg/dL, add ezetimibe. If still above "
        "goal, add PCSK9 inhibitor. For primary prevention with LDL-C >= 190: high-intensity statin. "
        "For diabetes aged 40-75: moderate-intensity statin; intensify if 10-year ASCVD risk >= 20%. "
        "Obtain fasting lipid panel 4-12 weeks after statin initiation to assess response. "
        "ICD-10: E78 (Disorders of lipoprotein metabolism)."
    ),
    # 13
    (
        "Diabetes Foot Care Protocol\n\n"
        "Perform comprehensive foot exam annually: inspect for deformities, skin integrity, "
        "ulceration. Test protective sensation with 10-g monofilament at 4 plantar sites per foot. "
        "Assess dorsalis pedis and posterior tibial pulses. Risk categories: 0 (normal sensation), "
        "1 (loss of sensation), 2 (loss of sensation + deformity or PAD), 3 (history of ulcer or "
        "amputation). Category 2-3 patients need referral to podiatry and therapeutic footwear. "
        "Educate on daily self-inspection, proper footwear, and avoiding walking barefoot. "
        "ICD-10: E11.621 (Type 2 diabetes with foot ulcer)."
    ),
    # 14
    (
        "Sepsis — Surviving Sepsis Campaign Bundle (Hour-1)\n\n"
        "Within 1 hour of sepsis recognition: (1) Measure serum lactate; remeasure if > 2 mmol/L. "
        "(2) Obtain blood cultures before antibiotics. (3) Administer broad-spectrum antibiotics. "
        "(4) Begin rapid infusion of 30 mL/kg crystalloid for hypotension or lactate >= 4 mmol/L. "
        "(5) Apply vasopressors (norepinephrine first-line) if hypotension persists after fluid "
        "resuscitation, targeting MAP >= 65 mmHg. Reassess volume status and tissue perfusion "
        "frequently. ICD-10: A41.9 (Sepsis, unspecified organism), R65.20 (Severe sepsis)."
    ),
    # 15
    (
        "Stroke — Acute Ischemic Stroke Protocol\n\n"
        "Door-to-CT time < 25 minutes. If eligible (onset < 4.5 hours, no contraindications), "
        "administer IV alteplase 0.9 mg/kg (max 90 mg), 10% as bolus, remainder over 60 minutes. "
        "For large vessel occlusion with onset < 24 hours, consider mechanical thrombectomy. "
        "Admit to stroke unit. Initiate DVT prophylaxis. Start antiplatelet therapy (aspirin) "
        "24 hours after thrombolysis. Statin within 48 hours. Swallowing assessment before oral "
        "intake. ICD-10: I63 (Cerebral infarction)."
    ),
    # 16
    (
        "Osteoporosis Screening and Treatment\n\n"
        "Screen with DXA scan: all women >= 65, men >= 70, and younger adults with risk factors. "
        "T-score <= -2.5 = osteoporosis; -1.0 to -2.5 = osteopenia. Calculate FRAX score for "
        "treatment decisions in osteopenia. First-line treatment: oral bisphosphonates (alendronate "
        "70 mg weekly or risedronate 35 mg weekly). Ensure adequate calcium (1200 mg/day) and "
        "vitamin D (800-1000 IU/day). Drug holiday after 5 years for oral or 3 years for IV "
        "bisphosphonates if stable. ICD-10: M81 (Osteoporosis without pathological fracture)."
    ),
    # 17
    (
        "Thyroid Disorder Management\n\n"
        "Hypothyroidism: initiate levothyroxine. Starting dose: 1.6 mcg/kg/day for young healthy "
        "adults, 25-50 mcg/day for elderly or cardiac patients. Check TSH 6-8 weeks after dose "
        "change. Target TSH 0.5-2.5 mIU/L for most patients. Take on empty stomach, 30-60 minutes "
        "before breakfast. Hyperthyroidism: confirm with low TSH + elevated free T4/T3. Graves' "
        "disease options: antithyroid drugs (methimazole preferred), radioactive iodine, or surgery. "
        "ICD-10: E03 (Hypothyroidism), E05 (Thyrotoxicosis)."
    ),
    # 18
    (
        "Pediatric Fever Management — Telehealth Triage Protocol\n\n"
        "Neonates (0-28 days) with fever >= 38.0C: advise immediate ED visit for full sepsis workup. "
        "Infants 29-60 days with fever >= 38.0C: ED evaluation recommended; low-risk criteria may "
        "allow close outpatient follow-up. Children 3 months-3 years with fever >= 39.0C: assess "
        "for UTI, AOM, pneumonia. Well-appearing children > 3 years: antipyretics (acetaminophen "
        "15 mg/kg q4h or ibuprofen 10 mg/kg q6h), hydration, re-evaluate if fever > 5 days or "
        "worsening. ICD-10: R50.9 (Fever, unspecified)."
    ),
    # 19
    (
        "Anxiety Disorders — GAD Management Protocol\n\n"
        "Screen with GAD-7 questionnaire. Score >= 10 indicates moderate anxiety warranting "
        "treatment. First-line pharmacotherapy: SSRI (sertraline, escitalopram) or SNRI "
        "(venlafaxine, duloxetine). Buspirone is an alternative for patients who cannot tolerate "
        "SSRIs. Avoid benzodiazepines for long-term management due to dependence risk. CBT is "
        "first-line psychotherapy. Reassess at 4-6 weeks; if inadequate response, optimize dose "
        "or switch class. ICD-10: F41.1 (Generalized anxiety disorder)."
    ),
    # 20
    (
        "Obesity Management — Clinical Protocol\n\n"
        "BMI >= 30 kg/m2 or >= 27 with comorbidities warrants pharmacotherapy. Lifestyle "
        "intervention (caloric restriction + 150 min/week moderate activity) is foundational. "
        "FDA-approved pharmacotherapy options: GLP-1 RAs (semaglutide 2.4 mg weekly, liraglutide "
        "3.0 mg daily, tirzepatide), orlistat, phentermine-topiramate. Consider bariatric surgery "
        "for BMI >= 40 or >= 35 with obesity-related comorbidities. Target 5-10% weight loss in "
        "first 6 months. Monitor for nutritional deficiencies post-bariatric surgery. "
        "ICD-10: E66 (Overweight and obesity)."
    ),
]


# ═══════════════════════════════════════════════════════════════════════════════
# Sample Drug Interaction Warnings (~20)
# ═══════════════════════════════════════════════════════════════════════════════

SAMPLE_DRUG_INTERACTIONS: list[dict[str, Any]] = [
    {
        "name": "Warfarin + Amiodarone",
        "description": (
            "Amiodarone inhibits CYP2C9 and CYP3A4, significantly increasing warfarin levels. "
            "INR may rise 1-2 points within 1-2 weeks. Reduce warfarin dose by 30-50% when "
            "starting amiodarone and monitor INR weekly for at least 4-6 weeks."
        ),
        "category": "drug_interaction",
        "interactions": "Warfarin, Amiodarone",
        "contraindications": "Monitor INR closely; risk of major bleeding",
    },
    {
        "name": "Metformin + IV Contrast Dye",
        "description": (
            "Iodinated contrast media can cause acute kidney injury, leading to metformin "
            "accumulation and lactic acidosis. Hold metformin on the day of contrast administration "
            "and for 48 hours after. Check renal function (eGFR) before resuming."
        ),
        "category": "drug_interaction",
        "interactions": "Metformin, Iodinated contrast",
        "icd10_codes": ["E11", "N17"],
    },
    {
        "name": "SSRI + MAOI",
        "description": (
            "Concurrent use of SSRIs (fluoxetine, sertraline, etc.) with MAO inhibitors "
            "(phenelzine, tranylcypromine, selegiline) can cause serotonin syndrome — a "
            "life-threatening condition with hyperthermia, rigidity, myoclonus, and autonomic "
            "instability. A washout period of at least 14 days (5 weeks for fluoxetine) is "
            "required when switching."
        ),
        "category": "drug_interaction",
        "interactions": "SSRIs, MAO Inhibitors",
        "contraindications": "Absolute contraindication — serotonin syndrome risk",
    },
    {
        "name": "ACE Inhibitor + Potassium-Sparing Diuretic",
        "description": (
            "ACE inhibitors (lisinopril, enalapril) combined with potassium-sparing diuretics "
            "(spironolactone, amiloride) increase the risk of life-threatening hyperkalemia. "
            "Monitor serum potassium within 1 week of initiation and regularly thereafter. "
            "Avoid if baseline K+ > 5.0 mEq/L or eGFR < 30."
        ),
        "category": "drug_interaction",
        "interactions": "ACE Inhibitors, Spironolactone, Amiloride",
        "icd10_codes": ["E87.5"],
    },
    {
        "name": "Simvastatin + Amlodipine",
        "description": (
            "Amlodipine inhibits CYP3A4, increasing simvastatin exposure and the risk of "
            "rhabdomyolysis. Do not exceed simvastatin 20 mg daily when co-administered with "
            "amlodipine. Consider switching to atorvastatin or rosuvastatin which are less "
            "affected by this interaction."
        ),
        "category": "drug_interaction",
        "interactions": "Simvastatin, Amlodipine",
        "contraindications": "Simvastatin > 20 mg/day with amlodipine; rhabdomyolysis risk",
    },
    {
        "name": "Methotrexate + NSAIDs",
        "description": (
            "NSAIDs reduce renal clearance of methotrexate, leading to elevated levels and "
            "increased toxicity (bone marrow suppression, mucositis, hepatotoxicity). Avoid "
            "concurrent use with high-dose methotrexate. With low-dose methotrexate for RA, "
            "use NSAIDs cautiously with monitoring of CBC and renal function."
        ),
        "category": "drug_interaction",
        "interactions": "Methotrexate, NSAIDs (ibuprofen, naproxen, etc.)",
    },
    {
        "name": "Digoxin + Amiodarone",
        "description": (
            "Amiodarone increases serum digoxin concentration by 70-100% through inhibition "
            "of P-glycoprotein and reduced renal clearance. Reduce digoxin dose by 50% when "
            "starting amiodarone. Target serum digoxin < 1.0 ng/mL. Monitor for signs of "
            "toxicity: nausea, visual disturbances, arrhythmias."
        ),
        "category": "drug_interaction",
        "interactions": "Digoxin, Amiodarone",
    },
    {
        "name": "Clopidogrel + Omeprazole",
        "description": (
            "Omeprazole (and to a lesser extent esomeprazole) inhibits CYP2C19, reducing "
            "the activation of clopidogrel and its antiplatelet effect. Use pantoprazole or "
            "famotidine as alternatives when gastroprotection is needed with clopidogrel. "
            "FDA boxed warning against concomitant use."
        ),
        "category": "drug_interaction",
        "interactions": "Clopidogrel, Omeprazole, Esomeprazole",
    },
    {
        "name": "Fluoroquinolones + QT-Prolonging Agents",
        "description": (
            "Fluoroquinolones (ciprofloxacin, levofloxacin, moxifloxacin) prolong the QT "
            "interval. Concomitant use with other QT-prolonging drugs (amiodarone, sotalol, "
            "ondansetron, haloperidol) increases the risk of torsades de pointes. Obtain "
            "baseline ECG. Avoid combinations when possible; if unavoidable, monitor QTc."
        ),
        "category": "drug_interaction",
        "interactions": "Fluoroquinolones, Amiodarone, Sotalol, Haloperidol",
    },
    {
        "name": "Lithium + NSAIDs",
        "description": (
            "NSAIDs decrease renal lithium clearance, increasing serum levels by 15-30%. "
            "This can precipitate lithium toxicity (tremor, confusion, renal impairment). "
            "If NSAID use is necessary, reduce lithium dose and monitor serum levels within "
            "5-7 days. Sulindac may be the safest NSAID option."
        ),
        "category": "drug_interaction",
        "interactions": "Lithium, NSAIDs",
        "icd10_codes": ["F31"],
    },
    {
        "name": "Potassium Chloride + ACE Inhibitors",
        "description": (
            "Supplemental potassium combined with ACE inhibitors or ARBs increases the risk "
            "of hyperkalemia, especially in patients with renal impairment or diabetes. "
            "Check serum potassium before starting and within 1 week. Avoid routine potassium "
            "supplementation unless documented hypokalemia."
        ),
        "category": "drug_interaction",
        "interactions": "Potassium supplements, ACE Inhibitors, ARBs",
    },
    {
        "name": "Opioids + Benzodiazepines",
        "description": (
            "FDA Black Box Warning: concurrent use of opioids and benzodiazepines increases "
            "the risk of profound sedation, respiratory depression, coma, and death. If "
            "co-prescription is unavoidable, use the lowest effective doses and shortest "
            "duration. Prescribe naloxone for patients on both drug classes."
        ),
        "category": "drug_interaction",
        "interactions": "Opioids (oxycodone, hydrocodone, etc.), Benzodiazepines (alprazolam, lorazepam, etc.)",
        "contraindications": "FDA Black Box Warning — respiratory depression and death",
    },
    {
        "name": "Carbamazepine + Oral Contraceptives",
        "description": (
            "Carbamazepine is a potent CYP3A4 inducer that significantly reduces the efficacy "
            "of combined oral contraceptives, increasing the risk of unintended pregnancy. "
            "Recommend non-hormonal contraception (copper IUD) or depot medroxyprogesterone "
            "acetate. Also applies to phenytoin, phenobarbital, and oxcarbazepine."
        ),
        "category": "drug_interaction",
        "interactions": "Carbamazepine, Oral Contraceptives",
    },
    {
        "name": "Ciprofloxacin + Tizanidine",
        "description": (
            "Ciprofloxacin strongly inhibits CYP1A2, causing a 10-fold increase in tizanidine "
            "AUC. This leads to severe hypotension and excessive sedation. This combination "
            "is contraindicated. If a fluoroquinolone is needed, use levofloxacin or "
            "moxifloxacin (non-CYP1A2 inhibitors)."
        ),
        "category": "drug_interaction",
        "interactions": "Ciprofloxacin, Tizanidine",
        "contraindications": "Absolute contraindication — 10-fold tizanidine increase",
    },
    {
        "name": "Trimethoprim-Sulfamethoxazole + Methotrexate",
        "description": (
            "TMP-SMX inhibits folate metabolism synergistically with methotrexate, dramatically "
            "increasing the risk of pancytopenia and bone marrow suppression. This combination "
            "should be avoided. Use alternative antibiotics. If unavoidable, increase leucovorin "
            "rescue and monitor CBC daily."
        ),
        "category": "drug_interaction",
        "interactions": "TMP-SMX (Bactrim), Methotrexate",
        "contraindications": "Severe pancytopenia risk — avoid combination",
    },
    {
        "name": "Grapefruit Juice + Statins",
        "description": (
            "Grapefruit juice inhibits intestinal CYP3A4, increasing bioavailability of "
            "simvastatin and lovastatin by up to 15-fold. This increases the risk of "
            "rhabdomyolysis. Atorvastatin is moderately affected. Rosuvastatin and pravastatin "
            "are not affected. Advise patients on simvastatin or lovastatin to avoid grapefruit."
        ),
        "category": "drug_interaction",
        "interactions": "Grapefruit, Simvastatin, Lovastatin, Atorvastatin",
    },
    {
        "name": "Allopurinol + Azathioprine",
        "description": (
            "Allopurinol inhibits xanthine oxidase, blocking the metabolism of azathioprine's "
            "active metabolite 6-mercaptopurine. This causes 3-5x accumulation of cytotoxic "
            "metabolites, leading to severe myelosuppression. If combination is essential, "
            "reduce azathioprine dose to 25-33% of standard dose. Monitor CBC weekly."
        ),
        "category": "drug_interaction",
        "interactions": "Allopurinol, Azathioprine, 6-Mercaptopurine",
    },
    {
        "name": "Sildenafil + Nitrates",
        "description": (
            "Phosphodiesterase-5 inhibitors (sildenafil, tadalafil) combined with organic "
            "nitrates (nitroglycerin, isosorbide) cause profound, potentially fatal hypotension. "
            "Absolutely contraindicated. Wait at least 24 hours after sildenafil (48 hours after "
            "tadalafil) before administering nitrates."
        ),
        "category": "drug_interaction",
        "interactions": "Sildenafil, Tadalafil, Nitroglycerin, Isosorbide",
        "contraindications": "Absolute contraindication — fatal hypotension risk",
    },
    {
        "name": "Clonidine + Beta-Blockers (Withdrawal)",
        "description": (
            "Abrupt discontinuation of clonidine while on a beta-blocker can cause rebound "
            "hypertensive crisis due to unopposed alpha-adrenergic stimulation. When "
            "discontinuing both agents, taper beta-blocker first over several days, then "
            "gradually taper clonidine over 1-2 weeks."
        ),
        "category": "drug_interaction",
        "interactions": "Clonidine, Beta-Blockers (metoprolol, atenolol, propranolol)",
        "icd10_codes": ["I10"],
    },
    {
        "name": "Spironolactone + Potassium Supplements",
        "description": (
            "Spironolactone is a potassium-sparing diuretic. Adding potassium supplements "
            "or potassium-containing salt substitutes substantially increases hyperkalemia risk. "
            "Monitor serum potassium at baseline, within 1 week, and monthly. Contraindicated "
            "if K+ > 5.0 mEq/L or severe renal impairment (eGFR < 30 mL/min)."
        ),
        "category": "drug_interaction",
        "interactions": "Spironolactone, Potassium Chloride, Salt Substitutes",
        "icd10_codes": ["E87.5"],
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
# Main CLI
# ═══════════════════════════════════════════════════════════════════════════════


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed the HealthOS Qdrant vector store with sample clinical data.",
    )
    parser.add_argument(
        "--collection",
        choices=[
            "clinical_guidelines",
            "drug_information",
            "all",
        ],
        default="all",
        help="Which collection(s) to seed (default: all).",
    )
    parser.add_argument(
        "--qdrant-url",
        default=None,
        help="Qdrant server URL.  Falls back to QDRANT_URL env var or settings default.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete and recreate collections before ingesting.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    # Late imports so the CLI arg parsing stays fast
    from healthos_platform.ml.rag.embeddings import EmbeddingService
    from healthos_platform.ml.rag.ingest import (
        ingest_clinical_guidelines,
        ingest_drug_database,
    )
    from healthos_platform.ml.rag.vector_store import ClinicalVectorStore

    embedding_service = EmbeddingService()
    store = ClinicalVectorStore(
        qdrant_url=args.qdrant_url,
        embedding_service=embedding_service,
    )

    collections_to_seed: list[str] = []
    if args.collection in ("all", "clinical_guidelines"):
        collections_to_seed.append("clinical_guidelines")
    if args.collection in ("all", "drug_information"):
        collections_to_seed.append("drug_information")

    # Optionally reset
    if args.reset:
        for coll in collections_to_seed:
            try:
                await store.delete_collection(coll)
                print(f"  Deleted collection: {coll}")
            except Exception:
                pass  # collection may not exist yet

    # Ensure collections exist
    for coll in collections_to_seed:
        await store.create_collection(coll)

    # Ingest
    if "clinical_guidelines" in collections_to_seed:
        print("Ingesting clinical guidelines...")
        count = await ingest_clinical_guidelines(
            filepath_or_texts=SAMPLE_CLINICAL_GUIDELINES,
            collection="clinical_guidelines",
            vector_store=store,
            source="sample_guidelines",
        )
        print(f"  Ingested {count} clinical guideline chunks.")

    if "drug_information" in collections_to_seed:
        print("Ingesting drug interaction warnings...")
        count = await ingest_drug_database(
            filepath_or_records=SAMPLE_DRUG_INTERACTIONS,
            collection="drug_information",
            vector_store=store,
            source="sample_drug_interactions",
        )
        print(f"  Ingested {count} drug interaction records.")

    # Summary
    print("\nCollection info:")
    for coll in collections_to_seed:
        try:
            info = await store.get_collection_info(coll)
            print(f"  {info['name']}: {info['points_count']} points ({info['status']})")
        except Exception as exc:
            print(f"  {coll}: error — {exc}")

    await store.close()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
