\# Campus Notice Board — Kubernetes Release Strategies



Student: Pema Choden  

Student number: 02230141



\## Purpose



Deploy a Campus Notice Board API on a local Kubernetes cluster and

measure request failures during Recreate, RollingUpdate, failed-release

rollback, blue/green switches, and a feature-flag rollout.



\## Environment



\- Windows with Docker Desktop using Linux containers

\- Docker Engine: 28.4.0

\- Docker Desktop: 4.46.0

\- kind: v0.33.0

\- kubectl: v1.32.2

\- Cluster Kubernetes: v1.32.2

\- Git: 2.49.0.windows.1

\- Application: Python standard library

\- Base image: python:3.12-alpine

\- Evidence of installed versions: evidence/t1-versions.txt



\## Prerequisites on a fresh Windows machine



1\. Install Git for Windows, including Git Bash.

2\. Install Docker Desktop, complete its required WSL 2/virtualisation

&#x20;  setup, and start the Linux container engine.

3\. Install kind and kubectl. This project uses the versions listed above.

4\. Place kind.exe in the user home directory, or adjust the commands below.

5\. Verify docker version, kubectl version --client, git --version,

&#x20;  and \& "$HOME\\kind.exe" version.

6\. Allow Docker to download the Python Alpine and kind node base images.



The Notice Board images are built locally and loaded directly into kind.

Application and monitor Pods use imagePullPolicy: Never.



\## A. Obtain source, create the cluster, and build images



Run in PowerShell. Replace YOUR\_REPOSITORY\_URL with this repository's URL.



```powershell

Set-Location $HOME

git clone YOUR\_REPOSITORY\_URL CTE412-notice-board

Set-Location "$HOME\\CTE412-notice-board"



\& "$HOME\\kind.exe" create cluster --config cluster/kind-cluster.yaml



docker build --build-arg APP\_VERSION=1.0.0 --build-arg STUDENT\_ID=02230141 -t notice-board:02230141-1.0.0 ./app

docker build --build-arg APP\_VERSION=1.1.0 --build-arg STUDENT\_ID=02230141 -t notice-board:02230141-1.1.0 ./app

docker build --build-arg APP\_VERSION=1.2.0-broken --build-arg STUDENT\_ID=02230141 -t notice-board:02230141-1.2.0-broken ./app



\& "$HOME\\kind.exe" load docker-image notice-board:02230141-1.0.0 notice-board:02230141-1.1.0 notice-board:02230141-1.2.0-broken --name cte412-02230141



kubectl apply -f manifests/base/namespace.yaml

kubectl config set-context --current --namespace=nb-02230141

kubectl apply -f manifests/base/quota.yaml

kubectl apply -f manifests/base/limits.yaml

```



Stop and resolve any failed command before continuing.



\## B. Recreate the final state of Task 8



Use this section when the cluster, namespace, quota, LimitRange, and loaded

images already exist. This is also the continuation of section A.



Run the whole block in PowerShell.



```powershell

\& {

&#x20;   $files = @(

&#x20;       "manifests/bluegreen/flags.yaml",

&#x20;       "manifests/bluegreen/blue.yaml",

&#x20;       "manifests/bluegreen/green.yaml",

&#x20;       "manifests/bluegreen/production-services.yaml",

&#x20;       "manifests/bluegreen/preview-service.yaml"

&#x20;   )



&#x20;   foreach ($file in $files) {

&#x20;       kubectl apply -f $file

&#x20;       if ($LASTEXITCODE -ne 0) {

&#x20;           throw "Failed to apply $file"

&#x20;       }

&#x20;   }



&#x20;   kubectl rollout status deployment/notice-board-blue -n nb-02230141 --timeout=180s

&#x20;   if ($LASTEXITCODE -ne 0) { throw "Blue rollout failed." }



&#x20;   kubectl rollout status deployment/notice-board-green -n nb-02230141 --timeout=180s

&#x20;   if ($LASTEXITCODE -ne 0) { throw "Green rollout failed." }



&#x20;   kubectl apply -f manifests/base/monitor.yaml

&#x20;   if ($LASTEXITCODE -ne 0) { throw "Monitor creation failed." }



&#x20;   kubectl wait --for=condition=Ready pod/monitor -n nb-02230141 --timeout=60s

&#x20;   if ($LASTEXITCODE -ne 0) { throw "Monitor is not ready." }



&#x20;   kubectl get deployments,pods,services,configmaps -n nb-02230141 -o wide



&#x20;   curl.exe --silent --show-error --fail http://127.0.0.1:30090/version

&#x20;   if ($LASTEXITCODE -ne 0) { throw "Version request failed." }



&#x20;   curl.exe --silent --show-error --fail http://127.0.0.1:30090/notices

&#x20;   if ($LASTEXITCODE -ne 0) { throw "Notices request failed." }

}

```



Expected final state:



\- Blue: three ready replicas of 1.0.0.

\- Green: three ready replicas of 1.1.0.

\- Production and preview Services select green.

\- FEATURE\_PINNED is "true".

\- Production /notices returns pinnedFirst: true and notice order 2, 1, 3.

\- The monitor is running.



Do not apply manifests/rolling/ during this final-state rebuild.

Those files belong to the earlier release experiments.



\## Monitoring and evidence



The original monitor ran continuously through Tasks 4–8.

Its session log is evidence/t9-monitor-full.log.

The monitor created during Task 9 is a new instance used for rebuild verification.



Run the summariser in Git Bash:



```bash

bash scripts/summarise.sh evidence/t8-monitor-log.txt

```



Experiment evidence is stored under evidence/.

The report is report/p06-report.md.



\## Cleanup



Save required evidence before cleanup.



```powershell

kubectl config set-context --current --namespace=default

\& "$HOME\\kind.exe" delete cluster --name cte412-02230141

\& "$HOME\\kind.exe" get clusters

```

