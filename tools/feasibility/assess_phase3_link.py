"""Separate registry enrollment, inferred trial dosing bounds and program labels."""
from datetime import date
import re


def assess_timing(study, announcement_date, origin, endpoint):
    for value in [origin, endpoint]:date.fromisoformat(value)
    if origin>=endpoint:raise ValueError('Invalid observation window')
    for field in ['study_first_posted_date','last_update_posted_date','results_first_posted_date']:
        if study.get(field):
            date.fromisoformat(study[field])
            if study[field]>endpoint:raise ValueError('Later registry posting cannot enter dated assessment')
    start=study.get('start_date')
    if start:date.fromisoformat(start)
    actual=(study.get('start_date_type') or '').upper()=='ACTUAL'
    phase=re.sub(r'[^A-Z0-9]','',(study.get('phase') or '').upper())
    within=bool(actual and start and origin<start<=endpoint and phase=='PHASE3')
    if announcement_date:date.fromisoformat(announcement_date)
    if actual and start and announcement_date and start>announcement_date:
        raise ValueError('First enrollment later than reported first dosing: conflicting sources')
    interval=({'lower':start,'upper':announcement_date} if within and announcement_date
              and origin<announcement_date<=endpoint else None)
    return {'phase3_enrollment_within_window':within,
        'registry_reported_start_date':start,'registry_start_type':study.get('start_date_type'),
        'registry_event_kind':'first_enrollment' if actual else 'estimated_start_not_event',
        'exact_first_dose_date':None,'first_located_dosing_report_date':announcement_date,
        'first_public_dosing_date':None,'conditional_trial_dosing_interval':interval,
        'interval_assumptions':['On-trial treatment follows enrollment',
            'Retained sponsor announcement accurately represents the dated report',
            'Trial-level first dosing does not establish first dosing in the experimental arm'],
        'interval_status':'inferred_from_two_sources_not_directly_observed' if interval else 'not_established',
        'strict_historical_event_certified':False,'clinical_training_label':None,'role':'evaluation_only'}
