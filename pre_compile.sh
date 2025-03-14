./waf clean

CC=clang CXX=clang++ ./waf configure --board sitl
CC=clang CXX=clang++ ./waf copter -v -j1 | tee compilation_logs
CC=clang CXX=clang++ ./waf build
# --no-rebuild

