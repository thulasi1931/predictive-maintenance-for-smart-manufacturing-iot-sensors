import React from "react";

export default function Metrics({ metrics }) {
  const values = metrics?.metrics;
  return <section><section className="page-title"><div><p>MODEL VALIDATION</p><h1>Random Forest performance</h1><span>Metrics were calculated on 2,000 unseen test rows after training on 8,000 rows.</span></div></section>{values ? <><div className="metric-grid">{[["Accuracy", values.accuracy], ["Precision", values.precision], ["Recall", values.recall], ["F1 score", values.f1_score], ["PR-AUC", values.pr_auc], ["ROC-AUC", values.roc_auc]].map(([name, value]) => <article className="card" key={name}><p>{name}</p><b>{(value * 100).toFixed(2)}%</b></article>)}</div><article className="card metric-note"><h2>How to explain these results</h2><p>Accuracy is overall correctness. Precision shows how often a predicted failure was really a failure. Recall shows how many real failures the model found. F1 balances precision and recall. Because failures are rare in this dataset, recall and PR-AUC matter more than accuracy alone.</p></article></> : <article className="card">Loading model metrics…</article>}</section>;
}
