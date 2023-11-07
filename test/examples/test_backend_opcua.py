import sys
sys.path.insert(0, "..")

from opcua import Client

client = Client("opc.tcp://localhost:4840/freeopcua/server/")

client.connect()

# Client has a few methods to get proxy to UA nodes that
#  should always be in address space such as Root or Objects
root = client.get_root_node()
print("Objects node is: ", root)


# Node objects have methods to read and write node attributes
#  as well as browse or populate address space
print("Children of root are: ", root.get_children())

# get a specific node knowing its node id
var = client.get_node("ns=2;i=2")
var2 = client.get_node("ns=2;i=3")
print(var)
print(var2)

# get value of node as a DataValue object
# var.get_data_value()

# get value of node as a python builtin
var.get_value()
var2.get_value()
# set node value using implicit data type
var.set_value(4.5)
var2.set_value(3.9)

# Now getting a variable node using its browse path. Next step.
myvar = root.get_child(["0:Objects", "2:MyObject", "2:MyVariable"])
obj = root.get_child(["0:Objects", "2:MyObject"])
print("myvar is: ", myvar)
print("myobj is: ", obj)
print(myvar.get_value())

# Close connection, remove subscriptions, etc
client.disconnect()
