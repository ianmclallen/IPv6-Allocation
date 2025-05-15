# IPv6 Allocation

## Introduction
While reading about IPv6 and the different address allocation methods I started looking for scripts that others may have written to help me out in doing my own IPv6 Address Plan. Sadly I had a hard time finding some, so I decided to start this repository and start scriptiong some of these methods out.

I have focused on 3 ways to do IPv6 address allocation: 
* Next available
* Random (coming soon)
* Sparse

My hope is that this will help others and save them some time.

## Usage
For each method I've added usage info. In the future I hope to add use cases and examples. 

#### Next Available

The next Available script has four input parameters: starting network, new prefix, starting position, and increment.

If you want to show all the possible /44 networks for 2001:db8::/40, then you just fill in the values for starting network and new prefix. But let’s say you want to list all the possible /44 networks but skip the first two, it would be starting network and new prefix and setting the starting position at two. Another example is if you want to show all the possible /44 networks, but you want to skip every other network, you will set the increment to a one. 

With the addition of starting position and increment options, more flexibility has been added to this type of network allocation.

#### Sparse
The Sparse allocation script has three parameters:

* Starting Parent Network
* New Prefix
* Number of desired new networks

Sparse Allocation calls on the left most significant bits to increment on the nibble boundary. For example: 2001:db8::/36 with a new prefix of /40, the bits will look like this:
- 0000
- 1000
- 0100
- 1100
- 0010
- 1010
- 0110
- 1110
- 0001
- 1001
- 0101
- 1101
- 0011
- 1011
- 0111
- 1111

This is all fine and good but what if you want to do sparse allocation outside the nibble boundary? That's what this script is capable of, for example: 2001:db8::/37 with a new prefix of /43, the bits will look like this:
- 000000
- 100000
- 010000
- 110000
- 001000
- 101000
- 011000
- 111000
- 000100
- 100100
- ......

From here it will go through and create a list of all possible binaries. The binaries are calculated based on the difference in prefix from the starting parent network and new prefix. From this list of binaries we construct the new IPv6 Network. 
