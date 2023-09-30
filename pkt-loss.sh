#!/bin/bash
cd /home/valentinaadelsflugel/go/pkg/mod/cache/download/github.com/tylertreat/comcast/@v/v1.0.1/github.com/tylertreat/comcast@v1.0.1
go build comcast.go
go run comcast.go --device=lo --packet-loss=10%  #if this doesnt work, search the device using: $ ip a
