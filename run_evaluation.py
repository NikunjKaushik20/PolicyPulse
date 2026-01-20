from src.evaluation import run_evaluation, compare_with_baseline, save_evaluation_results
from tests.test_queries import NREGA_TEST_QUERIES, RTI_TEST_QUERIES

def main():
    print("=" * 60)
    print("PolicyPulse Evaluation Suite")
    print("=" * 60)
    
    # run NREGA tests
    print("\n📊 Evaluating NREGA...")
    nrega_res = run_evaluation(NREGA_TEST_QUERIES, "NREGA")
    
    print(f"\n✅ NREGA Results:")
    print(f"   Year Accuracy: {nrega_res['accuracy_year']:.1%}")
    print(f"   Modality Accuracy: {nrega_res['accuracy_modality']:.1%}")
    print(f"   Both Correct: {nrega_res['accuracy_both']:.1%}")
    print(f"   Avg Top-1 Score: {nrega_res['avg_top1_score']}")
    
    save_evaluation_results(nrega_res, "evaluation_nrega.json")
    
    # RTI tests
    print("\n📊 Evaluating RTI...")
    rti_res = run_evaluation(RTI_TEST_QUERIES, "RTI")
    
    print(f"\n✅ RTI Results:")
    print(f"   Year Accuracy: {rti_res['accuracy_year']:.1%}")
    print(f"   Modality Accuracy: {rti_res['accuracy_modality']:.1%}")
    print(f"   Both Correct: {rti_res['accuracy_both']:.1%}")
    print(f"   Avg Top-1 Score: {rti_res['avg_top1_score']}")
    
    save_evaluation_results(rti_res, "evaluation_rti.json")
    
    # baseline comparison
    print("\n📊 Comparing with baseline...")
    
    nrega_comp = compare_with_baseline(NREGA_TEST_QUERIES, "NREGA")
    print(f"\n🏆 NREGA - PolicyPulse vs Baseline:")
    print(f"   PolicyPulse Accuracy: {nrega_comp['policypulse']['accuracy']:.1%}")
    print(f"   Baseline Accuracy: {nrega_comp['baseline']['accuracy']:.1%}")
    print(f"   Improvement: +{nrega_comp['improvement']}%")
    
    save_evaluation_results(nrega_comp, "comparison_nrega_baseline.json")
    
    rti_comp = compare_with_baseline(RTI_TEST_QUERIES, "RTI")
    print(f"\n🏆 RTI - PolicyPulse vs Baseline:")
    print(f"   PolicyPulse Accuracy: {rti_comp['policypulse']['accuracy']:.1%}")
    print(f"   Baseline Accuracy: {rti_comp['baseline']['accuracy']:.1%}")
    print(f"   Improvement: +{rti_comp['improvement']}%")
    
    save_evaluation_results(rti_comp, "comparison_rti_baseline.json")
    
    print("\n" + "=" * 60)
    print("✅ Evaluation Complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
