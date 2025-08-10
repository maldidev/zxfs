#!/bin/sh
mkdir ~/.zxfs
cp * ~/.zxfs
echo 'export PATH=$PATH:~/.zxfs' >> ~/.bashrc
echo done
