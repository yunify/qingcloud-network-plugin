# pitrix network plugin

OpenStack Neutron compatitable network plugin used in Pitrix system

## Test
```
# settings
sudo cp <project root>/test/*/*.init /etc
# modify /etc/*.init for your SDN controller
cd <project root>/test
./run_tests.sh
```
## NOTICE
This project contains source code form:
1. OpenStack Neutron with Apache License 2.0
2. networking_terra plugin from tethrnet.com