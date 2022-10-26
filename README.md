# UCR-Ursa-Major-Cluster-Templates

```bash
hpc-toolkit/ghpc create ./UCR-Ursa-Major-Cluster-Templates/ursa-major-spack-gromacs.yaml --vars project_id=<your projectid> -w

terraform -chdir=spack-gromacs/primary init && terraform -chdir=spack-gromacs/primary validate && terraform -chdir=spack-gromacs/primary apply -auto-approve
```
