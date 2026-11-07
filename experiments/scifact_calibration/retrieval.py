"""Read only the original TF-IDF retrieval arrays; no classifier or fitting."""
from __future__ import annotations

import io
from pathlib import Path
import unicodedata
import zipfile

from tether_engine.serde import canonical, encode, freeze, parse_json
from .inputs import VerifiedPreparation, capture, digest, need

ARRAY_KEYS={'retrieval_idf','pair_idf','index_data','index_indices','index_indptr',
            'label_coefficients','label_intercepts','rationale_coefficients','rationale_intercepts'}
RETRIEVAL_KEYS=('retrieval_idf','index_data','index_indices','index_indptr')


def _index(model_raw, arrays_raw, corpus):
    import numpy as np
    from scipy import sparse
    from sklearn.feature_extraction.text import TfidfVectorizer
    model=parse_json(model_raw)
    need(model.get('schema_version')==1 and model['arrays_bytes']==len(arrays_raw)
         and model['arrays_sha256']==digest(arrays_raw),'Original model/array binding differs')
    need(model['corpus']==corpus,'Original retrieval corpus differs from preserved preparation')
    with zipfile.ZipFile(io.BytesIO(arrays_raw)) as archive:
        members=archive.infolist()
        need(len(members)==len(ARRAY_KEYS) and {m.filename for m in members}=={k+'.npy' for k in ARRAY_KEYS}
             and sum(m.file_size for m in members)<=512*1024**2,'Invalid bounded numeric archive')
    # Unused classifier arrays remain unopened inside the captured ZIP.
    with np.load(io.BytesIO(arrays_raw),allow_pickle=False) as archive:
        arrays={k:archive[k].copy() for k in RETRIEVAL_KEYS}
    vocabulary=model['retrieval_vocabulary']; idf=arrays['retrieval_idf']
    need(isinstance(vocabulary,dict) and 0<len(vocabulary)<=100000
         and all(isinstance(k,str) and k and type(v) is int for k,v in vocabulary.items())
         and set(vocabulary.values())==set(range(len(vocabulary))),'Invalid retrieval vocabulary')
    need(idf.ndim==1 and len(idf)==len(vocabulary) and idf.dtype.kind=='f'
         and np.isfinite(idf).all() and (idf>=1).all(),'Invalid retrieval IDF')
    vectorizer=TfidfVectorizer(ngram_range=(1,2),lowercase=True,norm='l2',sublinear_tf=True,
                               max_features=100000,vocabulary=vocabulary)
    vectorizer.idf_=idf
    values,indices,indptr=(arrays[k] for k in ('index_data','index_indices','index_indptr'))
    need(values.ndim==indices.ndim==indptr.ndim==1 and values.dtype.kind=='f'
         and indices.dtype.kind in 'iu' and indptr.dtype.kind in 'iu'
         and np.isfinite(values).all() and (values>=0).all() and (values<=1+1e-12).all()
         and len(values)==len(indices) and len(indptr)==len(corpus)+1
         and indptr[0]==0 and indptr[-1]==len(values) and np.all(indptr[1:]>=indptr[:-1])
         and np.all(indices>=0) and np.all(indices<len(vocabulary)),'Invalid original retrieval CSR arrays')
    matrix=sparse.csr_matrix((values,indices,indptr),shape=(len(corpus),len(vocabulary)))
    # The original vectorizer may retain unsorted feature indices. Preserve its
    # operation order; reject duplicate coordinates without sorting the matrix.
    need(all(len(set(indices[indptr[i]:indptr[i+1]].tolist()))==int(indptr[i+1]-indptr[i])
             for i in range(len(corpus))),'Duplicate original retrieval CSR coordinates')
    return vectorizer,matrix


def rank_queries(authority, model_descriptor, *, purpose='calibrate', product_id='queries_calibration', k=5):
    """Return all ordered calibration requests and source-bound top-five records.

    The authority is produced by the mixed-role preparation audit. This consumer
    rechecks only its externally bound control, manifest and visible products;
    it never opens the original archive or any reference product.
    """
    need(purpose=='calibrate' and product_id=='queries_calibration' and type(k) is int and k==5,
         'Only calibration queries with the frozen top-five retrieval are authorized')
    need(isinstance(authority,VerifiedPreparation),'Verified preparation transition required')
    frame=parse_json(capture(authority.frame_proof,1024**2))
    need(frame['purpose']==purpose,'Transition purpose differs')
    manifest_raw=capture(frame['manifest']); manifest=parse_json(manifest_raw)
    need(canonical(manifest)==canonical(authority.manifest),'Preparation authority changed')
    base=Path(frame['manifest']['path']).parent; views={}; visible_proofs=[]
    for key,expected in (('corpus',authority.corpus),('queries_calibration',authority.queries)):
        meta=manifest['products'][key]
        need(purpose in meta['purposes'],'Product does not grant calibration purpose')
        p=dict(path=str(base/meta['path']),bytes=meta['bytes'],sha256=meta['sha256'])
        raw=capture(p); rows=[parse_json(line) for line in raw.splitlines()]
        need(canonical(rows)==canonical(expected),'Visible preparation view changed')
        views[key]=rows;visible_proofs.append(p)
    queries=views['queries_calibration']; corpus=views['corpus']
    need([q['id'] for q in queries]==list(authority.calibration_ids)==frame['expected_calibration_ids']
         and len(corpus)>=5,'Calibration schedule or corpus size differs')
    need(isinstance(model_descriptor,dict) and set(model_descriptor)=={'model','arrays'},'Exact original model descriptor required')
    model_raw=capture(model_descriptor['model']); arrays_raw=capture(model_descriptor['arrays'],256*1024**2)
    vectorizer,matrix=_index(model_raw,arrays_raw,corpus)
    import numpy as np
    from threadpoolctl import threadpool_limits
    ids=[d['doc_id'] for d in corpus]
    need(ids==sorted(set(ids)) and all(type(d) is int and d>=0 for d in ids),'Original corpus ordering differs')
    requests=[];retrieval=[]
    with threadpool_limits(limits=1):
        for query in queries:
            need(set(query)=={'id','claim'} and isinstance(query['claim'],str) and query['claim'].strip(),'Calibration query must be label-free')
            vector=vectorizer.transform([unicodedata.normalize('NFKC',query['claim'])])
            scores=np.asarray((matrix@vector.T).toarray()).ravel()
            need(len(scores)==len(ids) and np.isfinite(scores).all(),'Invalid retrieval similarity vector')
            order=sorted(range(len(ids)),key=lambda i:(-float(scores[i]),ids[i]))[:5]
            selected=[dict(doc_id=ids[i],rank=r+1,score=float(scores[i]),document_sha256=digest(canonical(corpus[i])))
                      for r,i in enumerate(order)]
            requests.append(dict(id=query['id'],claim=query['claim'],documents=[corpus[i] for i in order]))
            retrieval.append(dict(id=query['id'],retrieved=selected))
    return freeze(dict(schema_version=1,kind='sc05_calibration_retrieval_v1',purpose='calibrate',
        schedule=list(authority.calibration_ids),scheduled_pairs=len(queries)*5,requests=requests,retrieval=retrieval,
        transition=authority.frame_proof,visible_inputs=visible_proofs,model=model_descriptor,
        classifier_called=False,fit_performed=False,reference_products_read=False,
        tie_policy='descending_similarity_then_ascending_document_id'))
