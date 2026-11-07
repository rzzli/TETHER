"""Prepare a fresh explicit manifest from receipts without changing catalog or transport."""
import argparse
from pathlib import Path
from tether_engine.ingest import InputFile, InputManifest
from tether_engine.maintenance import write_new_json, validate_catalog
from tether_engine.serde import ContractError, read_json, safe_child


def prepare(raw_root, queues, catalog_path, destination):
    if destination.exists():
        raise ContractError('Manifest exists; preserve frozen inputs and choose a new output')
    catalog = read_json(catalog_path)
    validate_catalog(catalog)
    required = {'ot_target','ot_disease','ot_evidence','hgnc_symbols','tether_normalized_packets'}
    if not required.issubset({row['dataset_id'] for row in catalog['datasets']}):
        raise ContractError('Catalog lacks required products; use the reviewed maintenance workflow')
    raw_root = raw_root.resolve()
    files, missing, expected, seen = [], [], {}, set()
    for queue_path in queues:
        for row in read_json(queue_path)['files']:
            if row['dataset_id'] not in required - {'tether_normalized_packets'}:
                continue
            key = row['relative_path'].replace('\\','/')
            if 'sourceId=chembl' in key.split('/'):
                continue
            if key in seen:
                raise ContractError('Duplicate queued input path')
            seen.add(key)
            expected[row['dataset_id']] = expected.get(row['dataset_id'],0)+1
            relative = 'manifests/receipts/'+row['receipt_id']+'.json'
            receipt = safe_child(raw_root,relative)
            source = safe_child(raw_root,row['relative_path'])
            if not source.is_file() or not receipt.is_file() or read_json(receipt).get('status') != 'completed':
                missing.append(row['relative_path'])
            else:
                files.append(InputFile(row['dataset_id'],row['release_id'],row['relative_path'],relative))
    if not expected:
        raise ContractError('No supported inputs in selected queues')
    value = InputManifest(2,str(raw_root),tuple(files),expected,tuple(missing))
    write_new_json(destination,value)
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--raw-root',type=Path,required=True)
    parser.add_argument('--queue',type=Path,action='append',required=True)
    parser.add_argument('--catalog',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    value = prepare(args.raw_root,args.queue,args.catalog or args.project_root/'data/catalog/sources.json',args.output)
    print(f'Prepared {len(value.files)} inputs; {len(value.missing_inputs)} missing. Catalog and transport unchanged.')


if __name__ == '__main__':
    main()
