### Core Concept
The core concept here is to use policy routing to setup the routing table for the specific network card which we are using for data uploading. In such a way, we don't have any effects on CarFi's default routing behaviour.

### Step 1
You should configure the interface used for data uploading by yourself. By default, the interface is dhcp or ppp type. If not, modifications in scripts are proprably needed to adapt to new cases.
For instance, you can put a file named by the name of that interface inside the /etc/network/interfaces.d directory.

### Step 2
Copy uploader_up to /etc/network/if-up.d/, and make it be executable.
Copy uploader_down to /etc/network/if-post-down.d/, and make it be executable also.

### Step 3
From now, whenever the `ifup` or `ifdown` are called, the corresponding scripts are executed to configure the routing table for the interface properly.
