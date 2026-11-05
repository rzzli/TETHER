"""Fictional component/split tests; no task answers or production corpus."""
import copy
import unittest

from asof.serde import ContractError, canonical
from experiments.scifact.split import build_split, pair_rows, normalized_claim


def claim(key, docs, *, text=None, evidence=None):
    return {"id":key,"claim":text or f"Statement {key}","cited_doc_ids":docs,"evidence":evidence or {}}


class SplitTests(unittest.TestCase):
    def test_source_connection_quarantines_transitively(self):
        train=[claim(1,[10]),claim(2,[10,20]),claim(3,[30])]
        dev=[claim(100,[20])]
        result=build_split(train,dev)
        self.assertEqual(result["partitions"]["quarantined_train"],(1,2))
        self.assertEqual(result["partitions"]["dev"],(100,))
        self.assertEqual(result["group_by_claim"]["1"],result["group_by_claim"]["100"])

    def test_exact_normalized_text_connection(self):
        result=build_split([claim(1,[10],text="  Ａ  FACT ")],[claim(100,[20],text="a fact")])
        self.assertEqual(result["partitions"]["quarantined_train"],(1,))
        self.assertEqual(normalized_claim("  Ａ  FACT "),"a fact")

    def test_evidence_document_edges_included_outside_citations(self):
        evidence={"20":[{"label":"SUPPORT","sentences":[0]}]}
        result=build_split([claim(1,[10],evidence=evidence)],[claim(100,[20])])
        self.assertEqual(result["partitions"]["quarantined_train"],(1,))

    def test_input_order_invariance_and_fixed_proportions(self):
        train=[claim(i,[i]) for i in range(1,21)]; dev=[claim(100,[100])]
        left=build_split(train,dev); right=build_split(list(reversed(train)),dev)
        self.assertEqual(canonical(left),canonical(right))
        self.assertEqual([left["counts"][p] for p in ("fit","tune","calibration")],[14,3,3])
        ids=[k for p in ("fit","tune","calibration") for k in left["partitions"][p]]
        self.assertEqual(sorted(ids),list(range(1,21)))

    def test_components_cannot_split_across_internal_partitions(self):
        train=[claim(i,[i//2]) for i in range(2,42)]
        result=build_split(train,[claim(100,[100])])
        partitions={k:p for p,ids in result["partitions"].items() for k in ids}
        for first in range(2,42,2): self.assertEqual(partitions[first],partitions[first+1])

    def test_labels_do_not_change_group_assignment(self):
        train=[claim(i,[i],evidence={str(i):[{"label":"SUPPORT","sentences":[0]}]}) for i in range(1,21)]
        changed=copy.deepcopy(train)
        for row in changed: row["evidence"][str(row["id"])][0]["label"]="CONTRADICT"
        before=build_split(train,[claim(100,[100])]); after=build_split(changed,[claim(100,[100])])
        self.assertEqual(before["partitions"],after["partitions"])
        self.assertNotEqual(before["pair_label_counts"],after["pair_label_counts"])

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ContractError): build_split([claim(1,[1])],[claim(1,[2])])

    def test_missing_classes_explicitly_reported(self):
        result=build_split([claim(1,[1])],[claim(100,[100])])
        self.assertTrue(result["feasibility_issues"])

    def test_only_annotated_cited_negatives_constructed(self):
        rows=pair_rows([claim(1,[10,11],evidence={"10":[{"label":"SUPPORT","sentences":[0,2]},{"label":"SUPPORT","sentences":[3]}]})])
        self.assertEqual({row["doc_id"] for row in rows},{10,11})
        self.assertEqual(rows[0]["rationale_sentences"],[0,2,3])
        self.assertEqual(rows[0]["rationale_sets"],[[0,2],[3]])
        self.assertEqual(rows[1]["label"],"NEI")
        self.assertEqual(rows[1]["negative_basis"],"annotated_cited_document_without_evidence")


if __name__ == "__main__": unittest.main()
