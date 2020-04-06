#!/usr/bin/env python
import rospy
from mavros_msgs.msg import GlobalPositionTarget, State, PositionTarget
from mavros_msgs.srv import CommandBool, CommandTOL, SetMode
from geometry_msgs.msg import PoseStamped, Twist
from sensor_msgs.msg import Imu, NavSatFix
from std_msgs.msg import Float32, Float64, String
import time
from pyquaternion import Quaternion
import math
import threading
import yaml

global timesMovedFromPositionDesired 


class Px4Controller:

    def __init__(self):
        
        with open('/home/miguel/catkin_ws/src/Firmware/data.yaml') as f:
    
           data = yaml.load(f, Loader=yaml.FullLoader)
           for key, value in data.items():
              if key == "takeoff_height":
                 self.takeoff_height = value
              if key == "threshold_ground":
                 self.threshold_ground = value
              if key == "threshold_ground_minor":
                 self.threshold_ground_minor = value
              if key == "imu":
                 self.imu = value
              if key == "gps":
                 self.gps = value
              if key == "local_pose":
                 self.local_pose = value
              if key == "current_state":
                 self.current_state = value
              if key == "current_heading":
                 self.current_heading = value
              if key == "local_enu_position":
                 self.local_enu_position = value
              if key == "local_enu_position":
                 self.local_enu_position = value

              if key == "cur_target_pose":
                 self.cur_target_pose = value
              if key == "global_target":
                 self.global_target = value

              if key == "received_new_task":
                 self.received_new_task = value
              if key == "arm_state":
                 self.arm_state = value
              if key == "offboard_state":
                 self.offboard_state = value
              if key == "received_imu":
                 self.received_imu = value
              if key == "frame":
                 self.frame = value

              if key == "state":
                 self.state = value
        
        global timesMovedFromPositionDesired
        timesMovedFromPositionDesired = 0    

        '''
        ros subscribers
        '''
        # All the mavros topics can be found here: http://wiki.ros.org/mavros
        self.local_pose_sub = rospy.Subscriber("/mavros/local_position/pose", PoseStamped, self.local_pose_callback) # Subscriber of the local position by mavros 
                                                                                                                     # http://docs.ros.org/api/geometry_msgs/html/msg/PoseStamped.html
        self.mavros_sub = rospy.Subscriber("/mavros/state", State, self.mavros_state_callback) # Subscriber of the State by mavros http://docs.ros.org/api/mavros_msgs/html/msg/State.html
        self.gps_sub = rospy.Subscriber("/mavros/global_position/global", NavSatFix, self.gps_callback) # Subscriber of the global position by mavros 
                                                                                                        # http://docs.ros.org/api/sensor_msgs/html/msg/NavSatFix.html
        self.imu_sub = rospy.Subscriber("/mavros/imu/data", Imu, self.imu_callback) # Subscriber of imu data by mavros http://docs.ros.org/api/sensor_msgs/html/msg/Imu.html


        # Subscribe to the 4 custom topics published by the commander.py 
        self.set_target_position_sub = rospy.Subscriber("gi/set_pose/position", PoseStamped, self.set_target_position_callback) 
        self.set_target_yaw_sub = rospy.Subscriber("gi/set_pose/orientation", Float32, self.set_target_yaw_callback)
        self.custom_activity_sub = rospy.Subscriber("gi/set_activity/type", String, self.custom_activity_callback)
        self.custom_takeoff = rospy.Subscriber("gi/set_activity/takeoff", Float32, self.custom_takeoff_callback)
        self.avoid_right_obstacle = rospy.Subscriber("gi/avoidobstacle/right", Float32, self.avoid_right_obstacle_callback)
        self.avoid_right_obstacle_return = rospy.Subscriber("gi/avoidobstacle/right_return", Float32, self.avoid_right_obstacle_return_callback)

        '''
        ros publishers
        '''
        # It publishes to the position we want to move http://docs.ros.org/api/mavros_msgs/html/msg/PositionTarget.html
        self.local_target_pub = rospy.Publisher('mavros/setpoint_raw/local', PositionTarget, queue_size=10)
        
        '''
        ros services
        '''
        
        self.armService = rospy.ServiceProxy('/mavros/cmd/arming', CommandBool) # Service of Arming status http://docs.ros.org/api/mavros_msgs/html/srv/CommandBool.html
        self.flightModeService = rospy.ServiceProxy('/mavros/set_mode', SetMode) # Service mode provided by mavros http://docs.ros.org/api/mavros_msgs/html/srv/SetMode.html
                                                                                 # Custom modes can be seing here: http://wiki.ros.org/mavros/CustomModes


        print("Px4 Controller Initialized!")


    def start(self):
        rospy.init_node("offboard_node") # Initialize the node 
        for i in range(10): # Waits 5 seconds for initialization 
            if self.current_heading is not None:
                break
            else:
                print("Waiting for initialization.")
                time.sleep(0.5)
        #self.cur_target_pose = self.construct_target(0, 0, self.takeoff_height, self.current_heading)
        self.cur_target_pose = self.construct_target(0, 0, 0, self.current_heading) # Initialize the drone to this current position

        #print ("self.cur_target_pose:", self.cur_target_pose, type(self.cur_target_pose))

        for i in range(10):
            self.local_target_pub.publish(self.cur_target_pose) # Publish the drone position we initialite during the first 2 seconds
            #self.arm_state = self.arm() # Arms the drone (not necessary here)
            self.offboard_state = self.offboard() # Calls the function offboard the will select the mode Offboard
            time.sleep(0.2)

        '''
        main ROS thread
        '''
        #while self.arm_state and self.offboard_state and (rospy.is_shutdown() is False): # The code implemented the arm state, not necesary in our case
        while self.offboard_state and (rospy.is_shutdown() is False): # While offboard state is true and we don't shutdown it, do the loop

            self.local_target_pub.publish(self.cur_target_pose) # Publish to the mavros local_targe_pub our desired new position

            if (self.state is "LAND") and (self.local_pose.pose.position.z < self.threshold_ground_minor): # If we land and we are under 0.15 in the z position...

                if(self.disarm()): # ... we disarm the drone

                    self.state = "DISARMED"


            time.sleep(0.1) # Rate to publish


    def construct_target(self, x, y, z, yaw, yaw_rate = 1): # Function to create the message PositionTarget
        target_raw_pose = PositionTarget() # We will fill the following message with our values: http://docs.ros.org/api/mavros_msgs/html/msg/PositionTarget.html
        target_raw_pose.header.stamp = rospy.Time.now()

        target_raw_pose.coordinate_frame = 9 

        target_raw_pose.position.x = x
        target_raw_pose.position.y = y
        target_raw_pose.position.z = z

        target_raw_pose.type_mask = PositionTarget.IGNORE_VX + PositionTarget.IGNORE_VY + PositionTarget.IGNORE_VZ \
                                    + PositionTarget.IGNORE_AFX + PositionTarget.IGNORE_AFY + PositionTarget.IGNORE_AFZ \
                                    + PositionTarget.FORCE

        target_raw_pose.yaw = yaw
        target_raw_pose.yaw_rate = yaw_rate

        return target_raw_pose



    '''
    cur_p : poseStamped
    target_p: positionTarget
    '''
    def position_distance(self, cur_p, target_p, threshold=0.1): # Function that sees if our position and the target one is between our threshold 
        delta_x = math.fabs(cur_p.pose.position.x - target_p.position.x) # Calculates the absolute error between our position and the target
        delta_y = math.fabs(cur_p.pose.position.y - target_p.position.y)
        delta_z = math.fabs(cur_p.pose.position.z - target_p.position.z)

        if (delta_x + delta_y + delta_z < threshold): # the threshold is between the sum of our three values
            return True
        else:
            return False

    # Callbacks called in the initialization of the subscription to the mavros topics
    def local_pose_callback(self, msg): 
        self.local_pose = msg
        self.local_enu_position = msg


    def mavros_state_callback(self, msg):
        self.mavros_state = msg.mode


    def imu_callback(self, msg):
        global global_imu, current_heading
        self.imu = msg

        self.current_heading = self.q2yaw(self.imu.orientation) # Transforms q into degrees of yaw

        self.received_imu = True


    def gps_callback(self, msg):
        self.gps = msg



    def FLU2ENU(self, msg):
        # Converts the position of the map into the perspective of the drone using the following equations
        FLU_x = msg.pose.position.x * math.cos(self.current_heading) - msg.pose.position.y * math.sin(self.current_heading) # x*cos(alpha) - y*sin(alpha)
        FLU_y = msg.pose.position.x * math.sin(self.current_heading) + msg.pose.position.y * math.cos(self.current_heading) # x*sin(alpha) + y*cos(alpha)
        FLU_z = msg.pose.position.z

        return FLU_x, FLU_y, FLU_z

    # Callback of the target position
    def set_target_position_callback(self, msg):
        print("Received New Position Task!")
        # Depending of what are we looking we will look for a position respect the drone or respect the map
        if msg.header.frame_id == 'base_link': 
            '''
            BODY_FLU
            '''
            # For Body frame, we will use FLU (Forward, Left and Up)
            #           +Z     +X
            #            ^    ^
            #            |  /
            #            |/
            #  +Y <------body

            self.frame = "BODY"

            print("body FLU frame")

            ENU_X, ENU_Y, ENU_Z = self.FLU2ENU(msg) # Calls this function to get the ENU values

            ENU_X = ENU_X + self.local_pose.pose.position.x
            ENU_Y = ENU_Y + self.local_pose.pose.position.y
            ENU_Z = ENU_Z + self.local_pose.pose.position.z

            self.cur_target_pose = self.construct_target(ENU_X,
                                                         ENU_Y,
                                                         ENU_Z,
                                                         self.current_heading)


        else:
            '''
            LOCAL_ENU
            '''
            # For world frame, we will use ENU (EAST, NORTH and UP)
            #     +Z     +Y
            #      ^    ^
            #      |  /
            #      |/
            #    world------> +X

            self.frame = "LOCAL_ENU"
            print("local ENU frame")

            self.cur_target_pose = self.construct_target(msg.pose.position.x,
                                                         msg.pose.position.y,
                                                         msg.pose.position.z,
                                                         self.current_heading)

    '''
     Receive A Custom Activity
     '''
    # Custom activities depending on the String we are introducing
    def custom_activity_callback(self, msg):

        print("Received Custom Activity:", msg.data)

        if msg.data == "LAND": # Lands the drone ( z=0.1 so it is minor than the z we introduced 0.15 as minimum to disarm the drone)
            print("LANDING!")
            self.state = "LAND"
            self.cur_target_pose = self.construct_target(self.local_pose.pose.position.x,
                                                         self.local_pose.pose.position.y,
                                                         0.1,
                                                         self.current_heading)
        if msg.data == "TAKEOFF": # takeoff the drone into 0.1 position 
            print("TAKING OFF!")
            self.state = "TAKEOFF"
            self.cur_target_pose = self.construct_target(self.local_pose.pose.position.x,
                                                         self.local_pose.pose.position.y,
                                                         self.takeoff_height,
                                                         self.current_heading)
            self.arm_state = self.arm() # Arms the drone 
            if self.takeoff_detection(): # If it has been initialized correctly it will print one thing or the other
                print("Vehicle Took Off!")

            else:
                print("Vehicle Took Off Failed!")
                return

        if msg.data == "HOVER": # Hover the drone
            print("HOVERING!")
            self.state = "HOVER"
            self.hover()

        else:
            print("Received Custom Activity:", msg.data, "not supported yet!")



    def custom_takeoff_callback(self, msg): # Takes off the drone in the desired height we introduced
        print("Received Custom TakeOff!")

        self.cur_target_pose = self.construct_target(0, 0, msg.data, self.current_heading) # Sets the desired position
        self.arm_state = self.arm() # Arms the drone

        if self.takeoff_detection(): # Detect if the drone has takeoff correctly or not
            print("Vehicle Took Off!")

        else:
            print("Vehicle Took Off Failed!")
            return


    def avoid_right_obstacle_callback(self, msg): # Makes the drone moves X meters in the left direction to avoid an obstacle
        print("Received Avoiding Right Obstacle!")
        print(msg.data)

        if self.state is "HOVER": # If the drone is hovering (not taking off or landing)
            # Sets the desired position
            self.cur_target_pose = self.construct_target(self.local_pose.pose.position.x, self.local_pose.pose.position.y + msg.data, self.local_pose.pose.position.z, self.current_heading)
            global timesMovedFromPositionDesired
            timesMovedFromPositionDesired = timesMovedFromPositionDesired + 1 


    def avoid_right_obstacle_return_callback(self, msg): # Makes the drone return X meters in the right direction to the desired position
        print("Received Avoiding Right Obstacle!")
        print(msg.data)
        global timesMovedFromPositionDesired
        if self.state is "HOVER": # If the drone is hovering (not taking off or landing)
            if timesMovedFromPositionDesired > 0: # If the drone has moved from the desired position previously return X meters to this position
                # Sets the desired position
                self.cur_target_pose = self.construct_target(self.local_pose.pose.position.x, self.local_pose.pose.position.y - msg.data, self.local_pose.pose.position.z, self.current_heading)  
                timesMovedFromPositionDesired = timesMovedFromPositionDesired - 1 

 




    def set_target_yaw_callback(self, msg): 
        print("Received New Yaw Task!")

        yaw_deg = msg.data * math.pi / 180.0 # Converts the data into degrees from radians (pi = 180 degrees)
        self.cur_target_pose = self.construct_target(self.local_pose.pose.position.x,
                                                     self.local_pose.pose.position.y,
                                                     self.local_pose.pose.position.z,
                                                     yaw_deg)

    '''
    return yaw from current IMU
    '''
    # It returns the degrees we need to move, our desired rotation
    def q2yaw(self, q):
        if isinstance(q, Quaternion): # Checks if the variable is of the type Quaternion
            rotate_z_rad = q.yaw_pitch_roll[0]
        else:
            q_ = Quaternion(q.w, q.x, q.y, q.z) # Converts into Quaternion
            rotate_z_rad = q_.yaw_pitch_roll[0]

        return rotate_z_rad 


    def arm(self): #Arms the drone
        if self.armService(True):
            return True
        else:
            print("Vehicle arming failed!")
            return False

    def disarm(self): #Disarms the drone
        if self.armService(False):
            return True
        else:
            print("Vehicle disarming failed!")
            return False


    def offboard(self): # Initialize the drone into offboard service
        if self.flightModeService(custom_mode='OFFBOARD'):
            return True
        else:
            print("Vechile Offboard failed")
            return False


    def hover(self): # Hover the drone in the actual position

        self.cur_target_pose = self.construct_target(self.local_pose.pose.position.x,
                                                     self.local_pose.pose.position.y,
                                                     self.local_pose.pose.position.z,
                                                     self.current_heading)

    def takeoff_detection(self): # Detects if the drone has takeoff correctly
        if self.local_pose.pose.position.z > self.threshold_ground_minor and self.offboard_state and self.arm_state:
            return True
        else:
            return False


if __name__ == '__main__': # From here to the end calls the functions desired
    con = Px4Controller()
    con.start()

