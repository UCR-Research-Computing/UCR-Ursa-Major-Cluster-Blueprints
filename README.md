# UCR-Ursa-Major-Cluster-Templates

Google HPC Toolkit Templates used to create instances of the UCR Ursa Major Cluster.


`ghpc` is the tool that converts the yaml file to a directory that contains terraform code to create a cluster.

Example:
```bash
hpc-toolkit/ghpc create ./UCR-Ursa-Major-Cluster-Templates/ursa-major-spack-gromacs.yaml --vars project_id=<your projectid> -w
```
`terraform` is the command that builds the cluster based on the directory we created with the yaml file and the ghpc command.
```bash
terraform -chdir=spack-gromacs/primary init && terraform -chdir=spack-gromacs/primary validate && terraform -chdir=spack-gromacs/primary apply -auto-approve
```
