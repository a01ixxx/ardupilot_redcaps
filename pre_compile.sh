./waf clean

CC=clang CXX=clang++ ./waf configure --board sitl
CC=clang CXX=clang++ ./waf copter -v -j1
CC=clang CXX=clang++ ./waf build
# --no-rebuild

