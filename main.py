from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QListWidgetItem, QCheckBox, QFileDialog
from ms_graph import generate_access_token, GRAPH_API_ENDPOINT
from mainwindow_ui import Ui_MainWindow
import sys
import threading
import rosbag
import rospy
import requests
import datetime
import subprocess
import os


class MyMainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()

        self.setupUi(self)
        rospy.init_node('topic_recorder')
        self.setWindowTitle("ROS Bag Topic Selection")
        self.static_split.clicked.connect(self.static_split_handler)
        self.realtime_split.clicked.connect(self.realtime_split_handler)
        self.browse_button.clicked.connect(self.browse_bag_file)  # Connect browse_button to browse_bag_file
        self.output_bag = None
        self.bag_path = None
        self.upload_button.clicked.connect(self.upload_to_onedrive)
        self.recording_stop_event = threading.Event()
        self.realtime_recording_event = threading.Event()
        self.progress_bar_upload.setVisible(False)
        self.progress_label.setVisible(False)
        self.stop_recording_button.setVisible(False)
        self.ros_thread = None
        self.ros_realtime_thread = None
        self.upload_cancelled = False
        self.cancel_upload_button.setVisible(False)
        self.cancel_upload_button.clicked.connect(self.cancel_onedrive_upload)
        self.stop_recording_button.clicked.connect(self.stop_realtime_recording)
        self.wifi_update_timer = QTimer(self)
        self.wifi_update_timer.timeout.connect(self.display_wifi_connection)
        self.wifi_update_timer.start(1000)  # Update every 5 seconds

    def display_wifi_connection(self):
        try:
            result = subprocess.run(["iwgetid", "-r"], capture_output=True, text=True)
            if result.returncode == 0:
                ssid = result.stdout.strip()
                self.connection_label.setText(f"WiFi Status : Connected to {ssid}")
            else:
                self.connection_label.setText("WiFi Status : Not connected")
        except Exception as e:
            self.connection_label.setText("Error fetching WiFi connection")

    def browse_bag_file(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly

        bag_path, _ = QFileDialog.getOpenFileName(self, "Open Bag File", "", "ROS Bag Files (*.bag);;All Files (*)",
                                                  options=options)

        if bag_path:
            self.load_topics_from_bag(bag_path)
            QTimer.singleShot(0, self.display_bag_info)
            QTimer.singleShot(0, self.display_disk_capacity)
            self.bag_path = bag_path
            self.subscribe_label.setText('')
            self.size_label.setText('')
            self.upload_label.setText('')
            self.update_upload_response('')
            self.onedrive_size.setText('')
            self.folder_size.setText('')
            self.stop_recording_button.setVisible(False)

    def display_disk_capacity(self, limit=50):
        rosbags_folder_path = "/home/localadmin/RosBags"
        rosbags_folder_size = sum([os.path.getsize(os.path.join(dirpath, filename)) for dirpath, dirnames, filenames
                                   in os.walk(rosbags_folder_path) for filename in filenames])
        adjusted_folder_size_str = self.adjust_file_size(rosbags_folder_size)
        total_capacity = limit * (1024 ** 3)
        storage_percent = int((rosbags_folder_size / total_capacity) * 100)

        if storage_percent > 95:
            self.folder_size.setStyleSheet("color: red")
        self.folder_size.setText(
            f"Computer Drive Total Usage \n {adjusted_folder_size_str} / {limit} GB \n {storage_percent}% used")

    def load_topics_from_bag(self, bag_path):
        bag = rosbag.Bag(bag_path)
        topics = bag.get_type_and_topic_info().topics.keys()

        self.topic_list.clear()  # Clear existing items

        for topic in topics:
            item = QListWidgetItem(self.topic_list)
            checkbox = QCheckBox(topic)
            item.setSizeHint(checkbox.sizeHint())
            self.topic_list.addItem(item)
            self.topic_list.setItemWidget(item, checkbox)

        bag.close()

    def static_split_handler(self):
        if self.ros_thread is None or not self.ros_thread.is_alive():
            self.size_label.setText('')
            self.update_subscribe_response("Splitting in progress")
            self.ros_thread = threading.Thread(target=self.run_ros_node)
            self.ros_thread.start()
        else:
            rospy.loginfo("Splitting is already in progress.")

    def get_topics(self):
        selected_topics = []

        for index in range(self.topic_list.count()):
            item = self.topic_list.item(index)
            checkbox = self.topic_list.itemWidget(item)
            if checkbox.isChecked():
                selected_topics.append(checkbox.text())

        return selected_topics

    def run_ros_node(self):
        selected_topics = self.get_topics()
        if selected_topics:
            # Play the original bag and record selected topics
            input_bag_path = self.bag_path
            input_bag = rosbag.Bag(input_bag_path, 'r')

            current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            output_bag_path = f"/home/localadmin/RosBags/output{current_time}.bag"
            bag = rosbag.Bag(output_bag_path, 'w')

            try:
                for topic, msg, t in input_bag.read_messages(topics=selected_topics):
                    bag.write(topic, msg, t)
                    if self.recording_stop_event.is_set():
                        break

            finally:
                input_bag.close()
                bag.close()
                self.recording_stop_event.clear()  # Reset the event

                # Get the accurate file size
                bag_size = os.path.getsize(output_bag_path)
                self.update_subscribe_response("Splitting is done")
                correct_size = self.adjust_file_size(bag_size)
                self.size_label.setText(f"File Size: {correct_size}")
                QTimer.singleShot(0, self.display_disk_capacity)

    def upload_to_onedrive(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly

        bag_path, _ = QFileDialog.getOpenFileName(self, "Select Bag File to Upload", "",
                                                  "ROS Bag Files (*.bag);;All Files (*)",
                                                  options=options)

        if bag_path:
            self.update_upload_response('')
            self.onedrive_size.setText('')
            self.upload_bag_to_onedrive(bag_path)

    def display_onedrive_capacity(self, access_token):
        used_storage, total_storage = self.get_onedrive_quota(access_token)
        used_storage_percent = int((used_storage / total_storage) * 100)
        used_storage_str = self.adjust_file_size(used_storage)
        total_storage_str = self.adjust_file_size(total_storage)
        if used_storage_percent > 95:
            self.onedrive_size.setStyleSheet("color: red")
        self.onedrive_size.setText(
            f"OneDrive Total Usage \n {used_storage_str} / {total_storage_str} \n {used_storage_percent}% used")

    def upload_bag_to_onedrive(self, bag_path):
        app_id = 'f93c8fba-4e4c-4fae-9a83-ddeb6110638d'
        scopes = ['Files.ReadWrite']

        access_token = generate_access_token(app_id, scopes)  # You need to define this function
        headers = {
            'Authorization': 'Bearer ' + access_token['access_token'],
            'Content-Type': 'application/json'  # Set the correct Content-Type header
        }

        self.display_onedrive_capacity(access_token)
        file_name = os.path.basename(bag_path)
        file_size = os.path.getsize(bag_path)

        with open(bag_path, 'rb') as upload:
            media_content = upload.read()

        self.progress_bar_upload.setMaximum(file_size)
        self.progress_label.setVisible(True)  # Show the progress label
        self.progress_bar_upload.setVisible(True)
        self.cancel_upload_button.setVisible(True)  # Show the Cancel button

        bytes_uploaded = 0
        chunk_size = 1024  # Adjust chunk size as needed

        while bytes_uploaded < file_size and not self.upload_cancelled:
            chunk = media_content[bytes_uploaded:bytes_uploaded + chunk_size]  # Get the next chunk
            if not chunk:
                break

            requests.put(
                GRAPH_API_ENDPOINT + f'/me/drive/items/root:/{file_name}:/content',
                headers=headers,
                data=chunk
            )

            bytes_uploaded += len(chunk)
            self.progress_bar_upload.setValue(bytes_uploaded)
            QApplication.processEvents()  # Process the event loop to update the UI

        if self.upload_cancelled:
            self.update_upload_response(f"Uploading {file_name} to OneDrive cancelled.")
        else:
            self.update_upload_response(f"Uploading {file_name} to OneDrive completed.")

        # Reset UI elements
        self.progress_label.setVisible(False)  # Hide the progress label
        self.progress_bar_upload.setVisible(False)
        self.cancel_upload_button.setVisible(False)
        self.upload_cancelled = False  # Reset the upload_cancelled flag

    def update_subscribe_response(self, message):
        self.subscribe_label.setText(message)

    def adjust_file_size(self, size_in_bytes):
        if size_in_bytes < 1024:  # Less than 1 KB
            size_str = f"{size_in_bytes} bytes"
        elif size_in_bytes < 1024 * 1024:  # Less than 1 MB
            size_str = f"{size_in_bytes / 1024:.2f} KB"
        elif size_in_bytes < 1024 * 1024 * 1024:  # Less than 1 GB
            size_str = f"{size_in_bytes / (1024 * 1024):.2f} MB"
        else:
            size_str = f"{size_in_bytes / (1024 * 1024 * 1024):.2f} GB"

        return size_str

    def cancel_upload(self):
        self.upload_cancelled = True

    def update_upload_response(self, message):
        self.upload_label.setText(message)

    def get_bag_info(self, bag_path):
        result = subprocess.run(['rosbag', 'info', bag_path], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.splitlines()
        else:
            return ["Error fetching bag information."]

    def display_bag_info(self):
        if self.bag_path:
            # Clear existing items
            self.bag_info_list.clear()
            # Fetch bag information using rosbag info
            bag_info = self.get_bag_info(self.bag_path)

            # Populate the QListWidget with bag information
            for line in bag_info:
                self.bag_info_list.addItem(line)

    def cancel_onedrive_upload(self):
        self.upload_cancelled = True
        self.progress_label.setVisible(False)  # Hide the progress label
        self.progress_bar_upload.setVisible(False)
        self.update_upload_response("Upload cancelled.")

    def callback(self, msg, topic_name):
        # This is where you can process and record the incoming messages
        self.output_bag.write(topic_name, msg)

    def stop_realtime_recording(self):
        self.realtime_recording_event.set()  # Set the event to stop the recording
        self.stop_recording_button.setEnabled(False)  # Disable the stop button while stopping

    def realtime_split_handler(self):
        if self.ros_realtime_thread is None or not self.ros_realtime_thread.is_alive():
            self.size_label.setText('')
            self.update_subscribe_response("Real-time recording in progress")
            self.stop_recording_button.setEnabled(True)
            self.ros_realtime_thread = threading.Thread(target=self.realtime_record)
            self.ros_realtime_thread.start()
        else:
            rospy.loginfo("Real-time recording is already in progress.")

    def realtime_record(self):
        current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_bag_path = f"/home/localadmin/RosBags/output{current_time}.bag"
        self.output_bag = rosbag.Bag(output_bag_path, 'w')

        topics_to_record = self.get_topics()
        subscribers = []

        for topic in topics_to_record:
            subscribers.append(rospy.Subscriber(topic, rospy.AnyMsg, self.callback, callback_args=topic))

        self.stop_recording_button.setVisible(True)

        rate = rospy.Rate(10)  # Set the loop rate (10 Hz, adjust as needed)

        while not rospy.is_shutdown() and not self.realtime_recording_event.is_set():
            rate.sleep()  # Control the loop execution rate

        for sub in subscribers:
            sub.unregister()

        self.output_bag.close()
        # Get the accurate file size
        bag_size = os.path.getsize(output_bag_path)
        self.update_subscribe_response("Real-time recording is done")
        correct_size = self.adjust_file_size(bag_size)
        self.size_label.setText(f"File Size: {correct_size}")
        self.realtime_recording_event.clear()
        QTimer.singleShot(0, self.display_disk_capacity)

    def get_onedrive_quota(self, access_token):
        graph_api_endpoint = 'https://graph.microsoft.com/v1.0/me/drive'
        headers = {
            'Authorization': 'Bearer ' + access_token['access_token']
        }

        response = requests.get(graph_api_endpoint, headers=headers)
        drive_info = response.json()

        quota_info = drive_info.get('quota')
        if quota_info:
            used_storage = quota_info.get('used')
            total_storage = quota_info.get('total')
            return used_storage, total_storage
        else:
            raise Exception("Failed to retrieve OneDrive quota.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyMainWindow()
    window.show()
    sys.exit(app.exec_())
