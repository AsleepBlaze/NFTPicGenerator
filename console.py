#! /usr/bin/env python

import command

if __name__ == '__main__':
    args = command.gen.ap.parse_args()
    args.func(args)