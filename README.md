# containerlab-IP-Generator
 Note this is still a work in progress. <p>
Since Clos topology is pretty standard, it is often the best candidate for auto-configuration. As it stands SR Linux does not support unnumbered BGP. Hence this script. It does the following:-

1. Auto-assign IP to the point-to-point links on the fabric.
2. Draw the AS numbers from the topology file used by containerlab.
3. Generate a basic configuration with underlay eBGP enabled.<p>

The output of this script is intended to be used as input to Ansible scripts to push the config into the fabric. 
  
  
  # Usage
  
  Run the script **ipGenerator.py**. \
  The template and the topology files should be placed in the local directory for this to work. 
