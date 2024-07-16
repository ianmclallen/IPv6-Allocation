# IPv6 Allocation

## Introduction
While reading about IPv6 and the different address allocation methods I started looking for scripts that others may have written to help me out in doing my own IPv6 Address Plan. Sadly I had a hard time finding some, so I decided to start this repository and start scriptiong some of these methods out.

I have focused on 3 ways to do IPv6 address allocation: 
* Next available
* Random (coming soon)
* Sparse (coming soon)

My hope is that this will help others and save them some time.

## Usage
For each method I've added usage info. In the future I hope to add use cases and examples. 

#### Next Available

The next Available script has four input parameters: starting network, new prefix, starting position, and increment.

If you want to show all the possible /44 networks for 2001:db8::/40, then you just fill in the values for starting network and new prefix. But let’s say you want to list all the possible /44 networks but skip the first two, it would be starting network and new prefix and setting the starting position at two. Another example is if you want to show all the possible /44 networks, but you want to skip every other network, you will set the increment to a one. 

With the addition of starting position and increment options, more flexibility has been added to this type of network allocation.
