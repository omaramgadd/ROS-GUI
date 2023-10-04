# ROS-GUI
GUI Desktop App for handling ROS bags, recording selected topics in realtime and uploading selected bag to oneDrive account

## Usage

### Download and Run ROS Bag:

- Before running the app, ensure roscore is active, and play the desired ROS bag in the background. It is recommended to use the -l flag to keep the bag running.

### Run the GUI App:
- Execute the following command to start the GUI app: `python main.py`

### GUI Design
- The GUI layout was created using Qt Designer. You can modify the design by creating your preferred layout file inside the project folder and converting it to a Python file using the following command: `pyuic5 {layout_file}.ui -o mainwindow_ui.py`
- ![ezgif com-optimize](https://github.com/omaramgadd/ROS-GUI/assets/57623082/594a8543-fc78-4820-8d64-25fab6a1bb15)


### Usage Examples
To perform real-time recording, follow these steps:
- Download and run roscore and play the desired ROS bag in the background, preferably using the -l flag.
- Run the GUI app using the command: python main.py
- Select the desired topics and click on the "Real-time Split" button.

To perform static split, follow these steps:
- Ensure roscore is active.
- Run the GUI app using the command: python main.py
- Select the desired topics and click on the "Static Split" button.

When uploading to OneDrive for the first time, you must connect to the account from the browser and enter the code that will be displayed in the terminal


## Technologies Used
- PyQt5 for GUI design and interaction.
- ROS (Robot Operating System) Noetic for handling ROS bag files.
- Microsoft Graph API for interacting with OneDrive.
- Python 3.x for the backend logic and functionality.

## Features
- Static Splitting: Allows the user to split a ROS bag into selected topics and save them as a new bag file.
- Real-time Recording: Enables real-time recording of selected topics, creating a new bag file as data is received.
- OneDrive Integration: Supports uploading bag files to OneDrive for cloud storage and easy access.

## Code Overview

- The code employs PyQt5 for GUI management, ROS and rosbag for handling ROS-related operations, and Microsoft Graph API for OneDrive integration. It is structured as follows:

- Main Class: `MyMainWindow` inherits from `QMainWindow` and `Ui_MainWindow` for GUI initialization and interaction.

### Functionality:

- WiFi Status: Fetches and displays the current WiFi connection status.

- Browse Bag File: Allows the user to select a ROS bag file and loads available topics from the bag.

- Display Disk Capacity: Retrieves and displays the capacity of the storage location for ROS bags.

- Static Split Handler: Initiates the process of splitting selected topics into a new bag file.

- Run ROS Node: Plays the original bag file and records selected topics to a new bag.

- Upload to OneDrive: Allows the user to select a bag file and initiates the process of uploading it to OneDrive.

- Display OneDrive Capacity: Retrieves and displays the capacity of the OneDrive storage.

- Additional Utilities: Functions for formatting file sizes, fetching bag information, and managing UI elements.

## License
This project is licensed under the MIT License.

## Contact
For any questions, feedback, or suggestions, feel free to contact me.


  

  
