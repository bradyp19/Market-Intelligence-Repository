Iceberg Concurrency Model, Snapshots, and the Iceberg Spec (, 2025-06-16)
Source: https://www.starburst.io/blog/iceberg-concurrency-model-snapshots
Summary: Trino on ice I: A gentle introduction to Iceberg

Trino on ice II: In-place table evolution and cloud compatibility with Iceberg

Trino on ice III: Iceberg concurrency model, snapshots, and the Iceberg spec

Trino on ice IV: Deep dive into Iceberg internals

Welcome back to this blog series discussing the amazing features of Apache Iceberg. In the last two blog posts, we’ve covered a lot of cool feature improvements of Iceberg over the Hive model. I recommend you take a look at those if you haven’t yet.
Key Features:
• . In the last two blog posts, we’ve covered a lot of cool feature improvements of Iceberg over the Hive model
• . In the event that two writers attempt to commit at the same time, the writer that first acquires the lock successfully commits by swapping its snapshot as the current snapshot, while the second writer will retry to apply its changes again
Executive Insight: This announcement highlights new capabilities or strategic direction relevant to customers or the business.
