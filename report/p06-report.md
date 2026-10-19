# Rolling, Recreate and Blue/Green Releases of the Campus Notice Board on Kubernetes

**Module:** CTE412 Integrated Systems Technology  
**Student:** Pema Choden  
**Student number:** 02230141  
**Practical date:** 19 October 2026

## 1\. Objective

The objective was to deploy a Campus Notice Board API on Kubernetes and compare release strategies using observed request failures. I investigated Recreate, RollingUpdate, a deliberately unhealthy release and rollback, blue/green switching, and a ConfigMap-controlled feature flag. I also tested whether the final application state could be rebuilt from repository manifests. The emphasis was on collecting evidence rather than assuming that a successful deployment command guaranteed availability.

## 2\. Environment

|Component|Configuration|
|-|-|
|Host and shells|Windows; PowerShell and Git Bash|
|Docker|Docker Desktop 4.46.0; Engine 28.4.0; Linux containers|
|kind|v0.33.0|
|kubectl / Kubernetes|v1.32.2 / v1.32.2|
|Git|2.49.0.windows.1|
|Application|Python standard-library HTTP server; Python 3.12.15 observed in HTTP responses|
|Application base image|`python:3.12-alpine`|
|Cluster|`cte412-02230141`: one control-plane and two workers|
|Namespace|`nb-02230141`|
|External access|`127.0.0.1:30090`, mapped to NodePort 30090|

Three images were built from one source tree: `notice-board:02230141-1.0.0`, `notice-board:02230141-1.1.0`, and `notice-board:02230141-1.2.0-broken`. They were loaded directly into kind, and application manifests used `imagePullPolicy: Never`. The application ran as UID 10001 on port 8080 and exposed `/notices`, `/version`, and `/healthz`. The monitor reused the Alpine-based application image with its command overridden. The kind node image was separate Kubernetes infrastructure, not an Alpine application image.

The namespace quota allowed CPU requests of 1 core, memory requests of 1 GiB, CPU limits of 2 cores, memory limits of 2 GiB, 15 Pods, and four Services. Each application container and the monitor requested 50m CPU and 32 MiB memory, with limits of 100m and 64 MiB. Version and configuration evidence is recorded in `evidence/t1-versions.txt`, `evidence/t1-quota.txt`, and the repository manifests.

The monitor requested the internal Service's `/version` endpoint approximately every 0.5 seconds, with a 0.4-second timeout and no retries. It wrote UTC timestamps, OK/FAIL status, and response details. The same monitor was retained through Tasks 4–8; a new instance was created during the Task 9 rebuild. The at-rest baseline recorded 122 requests and zero failures (`evidence/t4-summary.txt`). The initial health test returned HTTP 503 at 0.205 seconds and HTTP 200 at 6.191 seconds (`evidence/t2-warmup.txt`).

## 3\. Results

|Release / experiment|Requests observed|Failed requests|Mixed-version window (seconds)|Peak number of Notice Board Pods|
|-|-:|-:|-|-|
|Recreate: 1.0.0 to 1.1.0|133|29|0 observed|Not established from reviewed evidence|
|RollingUpdate: 1.0.0 to 1.1.0|168|0|44.477|Not established from reviewed evidence|
|Broken release and rollback|351|0|0 observed; only 1.1.0 served|At least 4 observed; exact peak not established|
|Blue to green: first switch|53|0|Not calculated from the raw switch log|6 configured and retained; no replacements requested|
|Green to blue: second switch|53|0|Not calculated from the raw switch log|6 configured and retained; no replacements requested|
|Blue to green: third switch|52|0|Not calculated from the raw switch log|6 configured and retained; no replacements requested|
|Feature-flag experiment|644|0|0 version overlap; all responses were 1.1.0|Not established from reviewed evidence|

**Evidence:** `evidence/t5-recreate-summary.txt`, `evidence/t5-rolling-summary.txt`, `evidence/t5-mixed-windows.txt`, `evidence/t6-summary.txt`, `evidence/t6-failed-release-pods.txt`, `evidence/t7-switch-1-summary.txt`, `evidence/t7-switch-2-summary.txt`, `evidence/t7-switch-3-summary.txt`, and `evidence/t8-summary.txt`.

For Task 5, the observed mixed-version interval was measured from the first successful new-version response to the last successful old-version response, bounded below by zero. RollingUpdate's timestamps were 12:36:44.685Z and 12:37:29.162Z, giving 44.477 seconds. The initial script displayed 44 because of numeric conversion; the timestamp difference retains the milliseconds. Recreate's last old-version response preceded the first new-version response, so no overlap was observed.

The combined blue/green log recorded 157 requests with zero failures (`evidence/t7-all-switches-summary.txt`). Individual windows have boundary overlap and slightly different end points, so their counts are not an additive total. Version counts alone do not establish a blue/green mixed-version window: the raw response order must be checked, using 1.1.0 as the old version for the reverse switch.

**Measurement limitations:** The table distinguishes observed values from configuration-based expectations. Exact time-series Pod peaks were not established for every experiment. In particular, terminating Pods may coexist with replacements, so `replicas + maxSurge` is not automatically the measured total-Pod peak. The monitor Pod is excluded from application Pod counts. Zero sampled failures does not prove that no shorter interruption occurred between requests. The flag experiment can contain mixed configuration states even though every response reports version 1.1.0.

The final-state rebuild created both Deployments, three Services, the ConfigMap, and a new monitor. Both Deployments reached 3/3 readiness. Production returned version 1.1.0 and pinned-first ordering. The cluster was then deleted, while unrelated clusters remained (`evidence/t9-rebuild.txt`, `evidence/t9-rebuild-verification.txt`, and `evidence/t9-cluster-deleted.txt`). This verified reconstruction within the existing cluster before deletion, not installation on a fresh machine.

## 4\. Analysis

### A1. Ranking by failed requests and the mechanisms observed

Recreate ranked worst with 29 failed requests out of 133, approximately 21.8% of its capture. RollingUpdate, the broken-release recovery, all three blue/green switches, and the feature-flag experiment each recorded zero failures. Their capture lengths differed, so these are results of the specific experiments rather than universal failure rates.

In Recreate, the old Pods were removed before replacement Pods could pass the five-second warm-up. The log contained 82 successful old-version responses, 29 failures, and 22 successful new-version responses (`evidence/t5-recreate-summary.txt`). The 65.979-second capture duration includes successful traffic and must not be described as downtime.

RollingUpdate returned 98 responses from 1.0.0 and 70 from 1.1.0 without failures. Old capacity remained available while replacements became ready (`evidence/t5-rolling-summary.txt`). During the failed release, all 351 responses remained on 1.1.0; the broken Pod was running but unready (`evidence/t6-summary.txt`, `evidence/t6-failed-release-pods.txt`).

Blue/green changed Service selectors between already running colours. All three switch summaries recorded zero failures. The feature-flag rollout likewise retained successful service while replacing green Pods; its monitor recorded 644 successful responses (`evidence/t7-switch-1-summary.txt` through `t7-switch-3-summary.txt`; `evidence/t8-summary.txt`).

### A2. Why the broken release did not interrupt service, and default-setting predictions

The failure evidence reported `Progressing=False` with reason `ProgressDeadlineExceeded`, while `Available=True` remained present. Three healthy Pods stayed ready and one broken Pod remained 0/1 ready. After rollback, `kubectl diff` returned exit code 0 (`evidence/t6-conditions.txt`, `evidence/t6-failed-release-pods.txt`, and `evidence/t6-manifest-agreement.txt`).

The following predictions change one setting at a time, assuming healthy nodes and the same application:

|Setting used|Role and prediction if omitted/defaulted|
|-|-|
|Readiness probe on `/healthz`|Kept the broken Pod out of ready Service endpoints. Without readiness probing, it could receive traffic. Because its `/version` still returns 200, the monitor might still record zero failures while the unhealthy release was accepted.|
|`maxUnavailable: 0`|Preserved healthy capacity. The default 25% rounds down to zero for three replicas, so this particular replica count would have the same numerical setting.|
|`maxSurge: 1`|Allowed a replacement to start alongside the three healthy Pods. The default 25% rounds up to one for three replicas, again giving the same count here.|
|`minReadySeconds: 5`|Required sustained readiness. Its default of zero would remove this extra wait, but the broken Pod never became ready, so this change alone would not admit it.|
|`progressDeadlineSeconds: 60`|Made the stalled rollout report failure promptly. The default 600 seconds would delay reporting; it would not automatically roll back or necessarily cause request failures.|
|Liveness probe on `/version`|Tested process responsiveness independently of the intentionally failing health endpoint. Omitting liveness would remove that check; this broken process would still run. Pointing liveness at `/healthz` would instead cause repeated restarts.|
|`imagePullPolicy: Never`|Enforced local-image use. For these non-latest tags, the default is normally `IfNotPresent`; loaded images would work, but a missing image could trigger a registry pull.|

These distinctions follow Kubernetes rollout and probe behaviour \[1–3]. The key lesson is that endpoint selection protected traffic, while the monitor's chosen endpoint limited what “healthy” meant in the measurement.

### A3. RollingUpdate versus blue/green

**Mixed versions.** RollingUpdate had a measured 44.477-second sampled overlap. Blue/green changed the selected colour rather than replacing Pods, but a zero overlap cannot be inferred from aggregate counts. Endpoint propagation and in-flight requests can affect the transition. Individual switch logs remain necessary for exact observed windows (`evidence/t5-mixed-windows.txt`; `evidence/t7-switch-1-log.txt` through `t7-switch-3-log.txt`).

**Resources.** The configured rolling case allowed four non-terminating application Pods, whereas blue/green retained six. Including the monitor, these configurations account for 250m versus 350m CPU requests, 160 MiB versus 224 MiB memory requests, 500m versus 700m CPU limits, and 320 MiB versus 448 MiB memory limits. Both fit the namespace budget. These are calculations from declared requests and limits, not measured CPU or memory consumption; terminating Pods may temporarily add to totals \[4]. See `evidence/t7-quota.txt` and `evidence/t5-rolling-pod-watch.txt` for recorded resource and lifecycle evidence.

**Rollback time.** Blue/green can select the retained healthy colour without waiting for replacement Pods to start. Rolling rollback may require recreation and readiness checks, although Task 6 retained its healthy replicas throughout. The records `evidence/t6-events.txt` and `evidence/t7-switch-events.txt` contain timing markers, but exact comparable rollback durations have not been derived here. Therefore, no measured claim that one rollback was a specified number of seconds faster is made.

### A4. When Recreate is appropriate

A realistic example is an application upgrade involving an incompatible database schema where old and new application processes must not operate concurrently. An approved maintenance window can stop the old version, perform and verify the migration, and start the replacement. Recreate supports the application shutdown/startup sequence, but does not itself execute the migration or guarantee data consistency. Its measured availability cost in this lab was 29 failed requests and no observed version overlap (`evidence/t5-recreate-summary.txt`, `evidence/t5-mixed-windows.txt`). This illustrates a deliberate trade-off between continuity and preventing incompatible versions from running together.

### A5. What the feature flag changed and did not avoid

The flag enabled pinned-first sorting without rebuilding the 1.1.0 image. After activation, each of the three green Pods and production returned `pinnedFirst: true`, with notices ordered 2, 1, 3 (`evidence/t8-after.txt`). The feature and its data already existed in the image; the ConfigMap selected that behaviour rather than adding new application code.

The ConfigMap-only stage was recorded in `evidence/t8-configmap-only.txt`. Environment-based configuration is fixed when a container starts, so changing the ConfigMap alone does not update existing containers \[5]. A change to `cte412/flags-revision` in the Pod template initiated a declarative rolling replacement. This avoided an image build, but not Pod replacement, warm-up, readiness checks, or verification. The complete experiment recorded zero failed requests (`evidence/t8-summary.txt`).

## 5\. Reflection

One troubleshooting issue occurred during the manifest-agreement check after rollback. PowerShell reported `error: failed to run "diff": executable file not found in %PATH%`, and `kubectl diff` returned exit code 2. This was a missing local utility, not proof that Kubernetes and the manifest differed. Running the comparison in Git Bash, where `diff` was available, returned exit code 0 and confirmed agreement (`evidence/t6-manifest-agreement.txt`). This reinforced the importance of distinguishing tooling failures from application failures.

I also learned to record measurement boundaries before applying changes. The first broken-release attempt lacked the intended capture markers, so I preserved its evidence separately, recovered the healthy version, and repeated the experiment with a recorded start time. The submitted measured recovery contains 351 successful requests and no failures.

One uncertainty remains: how much shorter than the 0.5-second sampling interval a disruption could be, and whether Service endpoint propagation could create an overlap that the monitor missed. A future experiment should collect finer-grained request timings and a complete timestamped Pod lifecycle stream. This would also establish exact peak Pod counts instead of relying on rollout settings. The present results support zero observed failures in the successful strategies, not an unrestricted guarantee of zero downtime.

## 6\. References

All online references below were accessed on 19 October 2026.

1. Kubernetes. (n.d.). *Deployments (v1.32 documentation).* https://v1-32.docs.kubernetes.io/docs/concepts/workloads/controllers/deployment/
2. Kubernetes. (n.d.). *Deployments.* https://kubernetes.io/docs/concepts/workloads/controllers/deployment/
3. Kubernetes. (n.d.). *Liveness, readiness, and startup probes.* https://kubernetes.io/docs/concepts/workloads/pods/probes/
4. Kubernetes. (n.d.). *Resource management for Pods and containers.* https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/
5. Kubernetes. (n.d.). *Updating configuration via a ConfigMap.* https://kubernetes.io/docs/tutorials/configuration/updating-configuration-via-a-configmap/
6. Kubernetes SIGs. (n.d.). *kind: Quick start.* https://kind.sigs.k8s.io/docs/user/quick-start/

The assessment structure follows the supplied CTE412 assessed-lab handout. Numerical results are drawn from the practical's own terminal evidence and monitor summaries, rather than from the documentation.

