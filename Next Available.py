'''
Author: Ian McLallen
Email: imclallen@infoblox.com
Description: Next Available Allocation (or sequential) is straight forward. Take a larger prefix and break it down into smaller ones by enumerating it.
Todo:

Copyright (c) 2024 Ian McLallen / Infoblox

Redistribution and use in source and binary forms,
with or without modification, are permitted provided
that the following conditions are met:

1. Redistributions of source code must retain the above copyright
notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright
notice, this list of conditions and the following disclaimer in the
documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
'''

__version__ = '0.0.5'
__author__ = 'Ian Mclallen'
__author_email__ = 'imclallen@infoblox.com'
__license__ = 'BSD'

import re
from ipaddress import IPv6Network

def next_avaiable_allocation(network, new_prefix, start_with=0, incriment=1):
    
    if type(new_prefix) != int:
        i = type(new_prefix).__name__
        raise TypeError("New Prefix must be a integer, and not a {}".format(i))
    
    if re.search('/([0-9]{1}$|[0-9]{2}$|[0-9]{3}$)', network) is None:
        raise ValueError("Network Input must have a prefix at the end of the network")
    
    if IPv6Network(network).prefixlen >= new_prefix:
        raise ValueError("New Prefix must be longer then the network prefix length")
       
    network = IPv6Network(network)
    ipv6_nets = []

    for sn in network.subnets(new_prefix=new_prefix):
        ipv6_nets.append(sn)

    for i, final6Networks in enumerate(ipv6_nets[start_with::incriment]):
        print(final6Networks)

def main():
    '''
    Code logic
    '''
    exitcode = 0
    run_time = 0

    # Script Variables
    ipv6_network:str = "2001:db8::/44"
    new_prefix:int = 48
    starting_int:int = 0
    incriment:int = 1

    next_avaiable_allocation(ipv6_network, new_prefix, starting_int, incriment)

    return exitcode
    
if __name__== '__main__':
    exitcode = main()
    exit(exitcode)
## End Main ###
