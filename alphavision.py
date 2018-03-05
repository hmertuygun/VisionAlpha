# -*- coding: utf-8 -*-

from time import localtime, strftime
import time
import face_recognition
import cv2
import json
import io
import locale

db_location = "people.json"
logs_db = "logs.json"

def print_cool_text(): #generated via http://patorjk.com/software/taag
    print "__          __  _                               _______    "
    print "\ \        / / | |                             |__   __|   "
    print " \ \  /\  / /__| | ___ ___  _ __ ___   ___        | | ___  "
    print "  \ \/  \/ / _ \ |/ __/ _ \| '_ ` _ \ / _ \       | |/ _ \ "
    print "   \  /\  /  __/ | (_| (_) | | | | | |  __/       | | (_) |"
    print "    \/  \/ \___|_|\___\___/|_| |_| |_|\___|       |_|\___/ \n"
    print "__      ___     _                      _       _           "
    print "\ \    / (_)   (_)               /\   | |     | |          "
    print " \ \  / / _ ___ _  ___  _ __    /  \  | |_ __ | |__   __ _ "
    print "  \ \/ / | / __| |/ _ \| '_ \  / /\ \ | | '_ \| '_ \ / _` |"
    print "   \  /  | \__ \ | (_) | | | |/ ____ \| | |_) | | | | (_| |"
    print "    \/   |_|___/_|\___/|_| |_/_/    \_\_| .__/|_| |_|\__,_|"
    print "                                        | |                "
    print "                                        |_|                "


def recognize_people(ip=False, speed_over_accuracy=False):
    if ip:
        print "IP Camera guide:"
        print " 1) Type in the ip of destination"
        print " 2) Put in the port number, if none, hit enter."
        print " 3) Type the username that you use to log in with."
        print " 4) Type the password that you use to log in with.\n"
        camera_ip = raw_input(" 1) Ip of destination camera:")
        port_number = raw_input(" 2) Port Number:")
        user_name = raw_input(" 3) Username asked for authentication:")
        user_password = raw_input(" 4) Password asked for the authorization:")
        stream_link = raw_input( " 5) Live stream link of the camera:")
        
        video_hash = "http://"
        if (user_name is not None or user_name != "") and (user_password is not None or user_password != ""):
            video_hash += user_name + ":" + user_password + "@"
        video_hash += camera_ip
        if port_number is not None and port_number != "":
            video_hash += ":" + port_number
        if stream_link is not None and stream_link != "":
            video_hash += "/" + stream_link

        print "Attempting to connect to: \"" + video_hash + "\""
        try:
            video_capture = cv2.VideoCapture(video_hash)
        except:
            print "Connection failed!\n"
            return
    else:
        #Default port of a built-in laptop camera is 0.
        try:
            video_capture = cv2.VideoCapture(0)
        except:
            print "Error activating camera."
            return
        
    # Load a sample picture and learn how to recognize it.
    data = fetch_users_table()
    known_face_names, usr_path = skim_dict(data, "name"), skim_dict(data, "path")
    known_face_encodings = [face_recognition.face_encodings(face_recognition.load_image_file(usr_im))[0] for usr_im in usr_path]
    
    face_locations = []
    face_encodings = []
    face_names = []
    process_this_frame = True
    online_people = dict() # name => seen time
    unseen_people = dict() # seen person name => unseen time (for deleting countdown)
    
    while True:
        # Grab a single frame of video
        try:
            ret, frame = video_capture.read()
        except:
            print "Unable to access video stream."
            return

        if speed_over_accuracy:
            # Resize frame of video to 1/4 size for faster face recognition processing
            small_frame = cv2.resize(frame, (0,0), fx=0.25, fy=0.25)
        else:
            # Create small frame without resizing video stream for more accurate face recognition
            small_frame = cv2.resize(frame, (0, 0), fx=1, fy=1)

        # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
        rgb_small_frame = small_frame[:, :, ::-1]

        # Only process every other frame of video to save time
        if process_this_frame:
            # Find all the faces and face encodings in the current frame of video
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

            face_names = []
            
            for face_encoding in face_encodings:
                # See if the face is a match for the known face(s)
                match = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance = 0.5)
                name = "Unknown"
                if True in match:
                    match_index = match.index(True)
                    name = known_face_names[match_index].decode("utf-8")

                    if name not in online_people and name not in unseen_people: #first appearance
                        online_people.update({name:0})
                    elif name in online_people and name in unseen_people: #previously seen, but could not be seen in the last few seconds
                        online_people[name] += 1
                        unseen_people.pop(name, None)
                    elif name in online_people and name not in unseen_people: #previously seen
                        online_people[name] += 1
                    else: #not supposed to happen, error
                        print "An error occured."
                        return
                    unseen_people = {key:value+2 for key, value in unseen_people.items()}
                    for delperson in unseen_people.keys():
                        if unseen_people[delperson] > 30:
                            if online_people[delperson] > 5:
                                add_logs(delperson)
                            unseen_people.pop(delperson, None)
                            online_people.pop(delperson, None)
                    
                elif unseen_people is not None:
                    unseen_people = {key : value+2 for key, value in unseen_people.items()}

                print name + " " + strftime("%Y-%m-%d %H:%M:%S", localtime()) + " is online."
                face_names.append(name.split(" ")[0])

        else:
            # Print dicts for debugging
            debug = True
            if debug:
                print "\nOnline:          ",
                print online_people
                print "Recently unseen: ",
                print unseen_people

            for key in online_people.keys():
                if key in unseen_people.keys():
                    unseen_people[key] += 1
                else:
                    unseen_people.update({key:0})
            unseen_people = {key:value+1 for key, value in unseen_people.iteritems()}
            for delperson in unseen_people.keys():
                if unseen_people[delperson] > 30:
                    if online_people[delperson] > 5:
                        add_logs(delperson)
                    unseen_people.pop(delperson, None)
                    online_people.pop(delperson, None)
                
        process_this_frame = not process_this_frame

        # Display the results
        for (top, right, bottom, left), name in zip(face_locations, face_names):
            if speed_over_accuracy:
                # Scale back up face locations since the frame was scaled to 1/4 size
                top *= 4
                right *= 4
                bottom *= 4
                left *= 4
            #(else:) There is no need for this process if there was no resizing

            # Draw a box around the face
            #cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)

            # Draw a label with a name below the face
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, name.encode("utf-8"), (left + 5, bottom - 5), font, 0.8, (255, 255, 255), 1)

        # Display the resulting image
        try:
            cv2.imshow("Video", frame)
        except:
            print "Display failed"
            return
        
        # Hit 'q' on the keyboard to quit.
        if cv2.waitKey(1) & 0xFF == ord("q"):
            for person in online_people:
                if online_people[person] > 5:
                    add_logs(person)
            break

    # Release the webcam
    video_capture.release()
    cv2.destroyAllWindows()



def add_user(camera_port=0):
    #Since the default camera port is 0 for the laptop, the program terminates the laptop camera to take a photo.
    #It then asks for the name of the photo. Then, automatically adds .jpg extenion to make it work with the face recognition.
    camera = cv2.VideoCapture(camera_port)#Port is assigned as the value in the parameter. The default value is 0.
    time.sleep(1)#There is a 1 second sleep for the camera, because less will cause a black photo.(Camera takes the photo really fast, that's why.)
    return_value, image = camera.read()
    del(camera)#Deletes the camera process.
    name = raw_input("User's Name: ").decode(locale.getpreferredencoding())#Asks for the username.
    path = "users/" + str(count_users()) + ".jpg"#Saves the photo in the VisionAlpha-master/users file with the .jpg extension
    cv2.imwrite(path, image)#writes the image and the path.
    print name
    db_add_user(name, path)#Saves the given information to database file.


#db functions
def db_add_user(name, path):
    data = fetch_users_table()
    data.update({unicode(len(data)):{"name":name, "path": path}})
    with io.open(db_location, "w", encoding="utf-8") as users_json_file:
        users_json_file.write(json.dumps(data, ensure_ascii=False, indent=4, sort_keys=True))
        users_json_file.close()


def count_users():
    data = fetch_users_table()
    return len(data)


def print_users():
    data = fetch_users_table()
    print "\n"
    for id in sorted(data.iterkeys()): #sort dict
        if data[id]["name"] != "NULL":
            print id + "\t" + data[id]["path"] + "\t" + data[id]["name"]
    print "\n\n"


def delete_user(id=-1):
    print("-1 to cancel")
    if id is None or -1:
        print_users()
        id = raw_input("\n What is the id of the user to be deleted?").decode(locale.getpreferredencoding())
    if str(id) == "-1":
        print("Process terminated.")
    else:
        del_usr = select_user(id)
        print("The user " + del_usr + " is going to be deleted. Are you sure?")
        if raw_input("Press 1 to delete user, 0 to cancel").decode(locale.getpreferredencoding()) == "1":
            data = fetch_users_table()
            data[id]["name"] = "NULL"
            data[id]["path"] = "users/NULL.jpg"
            with io.open(db_location, "w", encoding="utf-8") as users_json_file:
                users_json_file.write(json.dumps(data, ensure_ascii=False, indent=4, sort_keys=True))
                users_json_file.close()
            print("Delete successful.")
        else:
            print("Operation canceled")


def select_user(id):
    data = fetch_users_table()
    return data[id]["name"]


def fetch_users_table():
    with io.open(db_location, "r", encoding="utf-8") as users_json_file:
        try:
            data = json.load(users_json_file)
            users_json_file.close()
        except ValueError:
            data = users_json_file.read()
            if data == "" or data is None:
                data = dict()
                users_json_file.close()
            else:
                print "\t#The database " + db_location + " seems to contain invalid JSON. Please fix it."
                users_json_file.close()
                return
    with io.open(db_location, "w", encoding="utf-8") as users_json_file:
        users_json_file.write(json.dumps(data, ensure_ascii=False, indent=4, sort_keys=True))
        users_json_file.close()
    return data


def skim_dict(data, param):
    skimmed = [data[val][param].encode("utf-8") for val in data if data[val][param] != "NULL"]
    return skimmed

#user log functions
def add_logs(name):
    current_time = strftime("%Y-%m-%d %H:%M:%S", localtime())
    log = fetch_logs()
    log.update({unicode(len(log)):{"time":current_time, "name":name}})
    with io.open(logs_db, "w", encoding="utf-8") as logs_json_file:
        logs_json_file.write(json.dumps(log, ensure_ascii=False, indent=4, sort_keys=True))
        logs_json_file.close()


def print_logs():
    log = fetch_logs()
    print "\n"
    for id in sorted(log.iterkeys()): #sort dict
        print id + "\t" + log[id]["time"] + "\t" + log[id]["name"]
    print "\n\n"


def fetch_logs():
    with io.open(logs_db, "r", encoding="utf-8") as logs_json_file:
        try:
            log = json.load(logs_json_file)
            logs_json_file.close()
        except ValueError:
            log = logs_json_file.read()
            if log == "" or log is None or log == "\"{}\"":
                log = dict()
                logs_json_file.close()
            else:
                print "\t#The database " + logs_db + " seems to contain invalid JSON. Please fix it."
                logs_json_file.close()
                return
    with io.open(logs_db, "w", encoding="utf-8") as logs_json_file:
        logs_json_file.write(json.dumps(log, ensure_ascii=False, indent=4, sort_keys=True))
        logs_json_file.close()
    return log


def run_program(): #main program
    print_cool_text()
    while True:
        print "\nOption 1: Face recognition from your camera"   #Recognizes faces from an default camera
        print "Option 2: Face recognition from an ip camera"    #Recognizes faces from an ip camera
        print "Option 3: Print user database"                   #Prints json database.
        print "Option 4: Add new user"                          #Adds a user to the system.
        print "Option 5: Remove a pre-existing user"            #Removes a user from the system.
        print "Option 6: Print user logs"                       #Prints the log database
        print "Option 7: Quit"                                  #Quits the program.
        usr_in = raw_input().decode(locale.getpreferredencoding())
        if usr_in == "1":
            recognize_people()
        elif usr_in == "2":
            recognize_people(True)
        elif usr_in == "3":
            print_users()
        elif usr_in == "4":
            add_user()
        elif usr_in == "5":
            delete_user()
        elif usr_in == "6":
            print_logs()
        elif usr_in == "7":
            print "Goodbye!"
            break

#run the program
run_program()

