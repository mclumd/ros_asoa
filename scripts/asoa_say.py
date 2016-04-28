#!/usr/bin/env python
import rospy
from std_msgs.msg import String
from asoa import say
from asoa import MismatchError
from asoa import MuteError
from asoa import FinishedSpeaking

status_pub = None

def asoa_callback(data):
    global  status_pub
    string_to_say = data.data
    # Eventually add code to publish to "asoa_status" topic that we're talking, etc.
    status_pub.publish("Saying \"" + string_to_say + "\"")
    try:
        say(string_to_say)
    except MismatchError:
        status_pub.publish("Mismatch on \"" + string_to_say + "\"")
    except MuteError:
        status_pub.publish("Muted on \"" + string_to_say + "\"")
    rospy.sleep(0.1)
    status_pub.publish("Finished saying \"" + string_to_say + "\"")
    
def main():
    global status_pub
    
    rospy.init_node('asoa_say')
    rospy.Subscriber("asoa_say_cmd", String, asoa_callback)  # Listen to asoa_say_cmd topic for strings

    status_pub = rospy.Publisher("asoa_status", String, queue_size=10)
    rospy.spin()

if __name__ == "__main__":
    main()
