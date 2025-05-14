'''
Author: Ian McLallen
Email: imclallen@infoblox.com

Notes: 

'''

import ipaddress
import time
import sys

#Used to find the time took to execute script
start_time = time.time()

#The list below defines the order of bits following the sparse allocation method.
sparse_allocation_binary_order = []

#setting final prefix to empty string, should be changed in script.
final_prefix = ""

#setting the number of networks requested as global variable
net_num = 0

def sparse_allocation(current_network, new_prefix, net_number):
 
 
    new_prefix_int = 0
    if type(new_prefix) == int:
        new_prefix_int = new_prefix
    
    if type(new_prefix) != str:
        raise ValueError("New Prefix must be in a string and not an integer")
    
    global final_prefix
    final_prefix = new_prefix 
       
    curr_prefix = ipaddress.IPv6Network(current_network).prefixlen
    global string_index
    
    string_index = int(curr_prefix)
    new_prefix_int = int(new_prefix.strip("/"))
    
    if curr_prefix > new_prefix_int:
        raise ValueError("New Prefix length must be larger then the current Network Prefix")
    
    if curr_prefix == new_prefix_int:
        raise ValueError("New Prefix and the current Network Prefix are the same size")
    
    if new_prefix_int > 128:
        raise ValueError("New Prefix length isn't a valid IPv6 Prefix. Prefix max length is 128")
    
    prefix_difference = new_prefix_int - curr_prefix
    
    #Something fun to have to see the large number.
    print("\n\nNumber of possible IP's in a /{} prefix: {:,}\n\n".format(curr_prefix, ipaddress.IPv6Network(current_network).num_addresses))
    
    global net_num
    net_num = net_number
    
    if (prefix_difference >= 18) or (net_num >= 5000):
        '''
        I've added this safe guard to prevent the script from running to long and eating CPU. 
        12 seemed to be a decent number for prefix difference. Also added limit on number of 
        networks requested. You don't want to list out 4 trillion /64 networks from a parent 
        /32 prefix (literally did this, trust me it sucked). Added number of possible networks 
        and a way for you to continue if you so desire. 
        '''
        
        print("""\
            The difference between the prefixes is rather large, the number of possible networks are: {:,}
            Trying to iterate through this could be time and resource consuming.\n""".format((2**prefix_difference)))
        
        opt = input("If you still want to continue please enter 'y', if not please enter 'n': ")
           
        while True:
        
            if opt.lower() == "n" or opt.lower() == "no":
                print('\n\nYou have chosen wisely!!\n\n')
                sys.exit()
                
            elif opt.lower() == "y" or opt.lower() == "yes":
                print('\n\nMay the odds be ever in your favor.\n\n')
                break
                
            else:
                #Should not have gotten to this point. This is the only NameError in the script.
                raise NameError
            
        generate_binary(prefix_difference, current_network)

    
    generate_binary(prefix_difference, current_network)


def generate_binary(prefix_diff, current_network):
    '''
    Why use a list for this and not a generator? I have spent time writting 
    the generator and it is much faster but at the cost of using duplicates.
    If you have a larger difference in prefixes with a lower number of networks
    the chances of duplicates are small. The lower the difference in prefixes
    and higher number of networks, the more prone you are to having duplicates.
    We can deduplicate the results but then you won't get the number of networks
    you wanted. 
    Using a list and removing what was used was the only way to fix this.
    '''
    for i in range(2**prefix_diff):
        # Format the number 'i' as binary, remove the '0b' prefix, and pad with zeros up to 'n' digits
        binary = format(i, 'b').zfill(prefix_diff)
        # Reverse the string and append the list of binary
        i = (binary[::-1])
        sparse_allocation_binary_order.append(i)
    
    #Checking that the number of new networks isn't zero. This makes no sense to do but still gonna check for it
    if net_num == 0:
        raise ValueError("Number of New Networks must be greater than zero")
    
    #This checks to make sure the number of networks desired isn't greater than what's possible.
    elif net_num > len(sparse_allocation_binary_order):
        raise ValueError("Number of New Networks exceeds number possible networks {0}. \n \nPlease use a \
                        max of {0} for number of networks".format(len(sparse_allocation_binary_order)))
        
    #And finally we execute the next function on this journey with possible networks less than or equal to the max
    elif net_num <= len(sparse_allocation_binary_order):
        select_binary(sparse_allocation_binary_order, current_network)
                
    #A safe guard raise that should not be needed but is there in case I missed something.    
    else:
        raise ValueError("A value was given that wasn't thought while writing this. Please file an Issue")


def select_binary(binary_lst, current_network):
    
    '''
    Here we are iterating through the number of networks specified
    in the beginning. Between the Random scipt and this one, 
    here is where the only difference really is.
    '''
    
    for i in range(0,net_num):
        binary_being_used = sparse_allocation_binary_order[i]
        sparse_allocation_execute(binary_being_used, current_network)



def sparse_allocation_execute(new_binary, ipv6_network):
    
    '''
    Here we have finally arrived to the function that's taking 
    everything and bringing it together to make your new networks.
    Each line should have a comment explaining what it's doing.
    Overkill, maybe. Helpful.....hopefully
    '''
    
    #Making new binary a string
    new_binary = str(new_binary)
    
    try:
        #Show full IPv6 network. This is needed to change into binary
        network1 = ipaddress.IPv6Network(ipv6_network).exploded
        
        # Parse the IPv6 network
        network = ipaddress.IPv6Network(network1, strict=False)

        # Convert the network address string into an integer and then binary
        binary_network = bin(int(network.network_address))[2:]  # [2:] Removes the '0b' prefix

        # Pad the beginning with zeros to ensure 128 bits
        network_str = (binary_network.zfill(128))
        
        #Magic time. Add the binary into the correct place based on the current prefix
        network_with_new_binary = network_str[:string_index] + new_binary
        
        #Now we add zeros to the end of the string until it's 128 bits long
        #While also converting the string into an integer
        new_ipv6_address_integer = int(network_with_new_binary[:128].ljust(128, '0'), 2)
     
        #taking the integer and processing it through IPv6address module, then making it a string and adding the new prefix 
        new_ipv6_address_with_prefix = str(ipaddress.IPv6Address(new_ipv6_address_integer))+final_prefix
        
        #Finally taking the new network and running through the IPv6Network module. This is what's returned
        new_ipv6_address_with_prefix = ipaddress.IPv6Network(new_ipv6_address_with_prefix)
        
        #And at long last we have arrived at your newly created network. Ta-da
        print(new_ipv6_address_with_prefix)

    except:
        #At this point in the script shouldn't be any errors, but added a raise in case.
        raise ValueError("A value in function sparse_allocation_execute is something I hadn't considered. Please file an Issue")


# Example usage
ipv6_network = "2001:db8::/32"
new_prefix = "/60"
number_of_networks = 500
sparse_allocation(ipv6_network, new_prefix, number_of_networks)

#Prints time taken to run script. Can be removed without affecting functionality
print("\n--- %s seconds ---" % (time.time() - start_time))