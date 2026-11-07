"""Conservative reconstructed bounds for date-only registry public postings.

This is an explicit civil-date assumption, never a claimed NLM timezone or a
substitute for original-version proof. It does not produce an outcome label.
"""
from datetime import date, datetime, timedelta, timezone
import re

from tether_engine.serde import ContractError

POLICY_ID = 'aact-public-date-offset-envelope-v1'


def publication_bounds(value):
    if value is None or re.fullmatch(r'\d{4}(?:-\d{2})?', str(value)):
        return {'status':'unknown','lower':None,'upper_exclusive':None,
                'reason':'Missing or partial public posting date'}
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):
        raise ContractError('Public posting date must retain ISO date precision')
    try:
        day=date.fromisoformat(value)
        midnight=datetime.combine(day,datetime.min.time(),tzinfo=timezone.utc)
        lower=midnight-timedelta(hours=14)
        upper=midnight+timedelta(days=1,hours=12)
    except (ValueError,OverflowError) as error:
        raise ContractError('Invalid public posting date') from error
    return {'status':'reconstructed','lower':lower.isoformat(),
            'upper_exclusive':upper.isoformat(),'reason':
            'Assumed civil posting date with unspecified conventional UTC offset in [-12,+14] hours'}


def version_eligibility(*, last_update_posted_date, cutoff_at, first_posted_date=None):
    try:
        cutoff=datetime.fromisoformat(cutoff_at.replace('Z','+00:00'))
        if cutoff.tzinfo is None or cutoff.utcoffset()!=timedelta(0):
            raise ValueError('UTC required')
    except (ValueError,AttributeError) as error:
        raise ContractError('Ascertainment cutoff needs explicit UTC') from error
    bounds=publication_bounds(last_update_posted_date)
    initial=publication_bounds(first_posted_date)
    if (bounds['status']=='reconstructed' and initial['status']=='reconstructed' and
            first_posted_date>last_update_posted_date):
        raise ContractError('Latest posting date precedes initial posting')
    if bounds['status']=='unknown':
        status='held_missing_version_date'
    elif datetime.fromisoformat(bounds['upper_exclusive'])<=cutoff:
        status='eligible_reconstructed_date_bound'
    elif datetime.fromisoformat(bounds['lower'])>=cutoff:
        status='held_after_cutoff'
    else:
        status='held_boundary_uncertain'
    return {'policy_id':POLICY_ID,'status':status,'last_update_posted_date':last_update_posted_date,
            'first_posted_date':first_posted_date,'cutoff_at':cutoff_at,
            'availability_bounds':bounds,'strict_timestamp_qualified':False,
            'original_version_bytes_qualified':False,'clinical_label':None,
            'held_version_policy':'Recover qualified earlier version or retain missingness; never exclude the origin member or assign a negative'}
