#!/bin/sh
 
### BEGIN INIT INFO
# Provides:          dqmusicbox
# Required-Start:    $remote_fs $syslog
# Required-Stop:     $remote_fs $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: DQMusicBox - start dqmusicbox Python program as a service
# Description:       DQMusicBox - start dqmusicbox Python program as a service
### END INIT INFO

#This program is free software: you can redistribute it and/or modify it 
#under the terms of the GNU General Public License as published by the 
#Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.

#This program is distributed in the hope that it will be useful, but 
#WITHOUT ANY WARRANTY; without even the implied warranty of 
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#This script's sole purpose is to start a Python program as a service.
#Nonetheless, I wanted to follow the rules with this script.
#So here is the documentation and the examples that I used in writing this script.
#http://blog.scphillips.com/posts/2013/07/getting-a-python-script-to-run-in-the-background-as-a-service-on-boot/
#http://www.thegeekstuff.com/2012/03/lsbinit-script
#http://refspecs.linuxfoundation.org/LSB_3.1.0/LSB-Core-generic/LSB-Core-generic/iniscrptfunc.html
#https://wiki.debian.org/LSBInitScripts
#https://stackoverflow.com/questions/1603109/how-to-make-a-python-script-run-like-a-service-or-daemon-in-linux
#https://wolfpaulus.com/technology/pythonlauncher/
#http://archives.aidanfindlater.com/blog/2009/09/04/sample-init-d-script/

case "$1" in

    start)
        start-stop-daemon --start --background --pidfile /var/run/dqmusicbox.pid --make-pidfile --user root --chuid root --startas /home/pi/dqmusicbox/bin/dqmusicbox.py
        #do_start
        ;;

    stop)
        start-stop-daemon --stop --pidfile /var/run/dqmusicbox.pid  --retry 20
        #do_stop
        ;;
 
    restart|reload|force-reload)
        start-stop-daemon --stop --pidfile /var/run/dqmusicbox.pid  --retry 20
        start-stop-daemon --start --background --pidfile /var/run/dqmusicbox.pid --make-pidfile --user root --chuid root --startas /home/pi/dqmusicbox/bin/dqmusicbox.py
        ;;
 
    status)
        status_of_proc "dqmusicbox" "/home/pi/dqmusicbox/bin/dqmusicbox.py" && exit 0 || exit $?
        ;;
    *)
        echo "Usage: /etc/init.d/dqmusicbox.sh {start|stop|restart|force-reload|status}"
        exit 1
        ;;
 
esac
exit 0
