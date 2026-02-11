# QR & Barcode Authentication System

A comprehensive Python-based desktop application for authenticating, logging, and managing QR codes and barcodes. Built with a modern UI using PySide6 and powered by OpenCV for scanning.

## features

- **Authentication System**: Scan QR codes/barcodes to verify authorized access.
- **Access Logging**: Automatically logs authorized and unauthorized attempts with timestamps.
- **Management**: Easily register new authorized codes via the app interface.
- **Generators**: Create custom QR codes and Barcodes (supports multiple formats like EAN-13, Code128, etc.).
- **Universal Scanner**: Scan any code and copy its content to the clipboard.
- **Modern UI**: Dark-themed user interface with sound feedback and responsive design.

## Prerequisites

- Python 3.8+
- Windows OS (due to `winsound` usage)
- Webcam

## Installation

1.  Clone the repository or download the source code.
2.  Install the required dependencies:

    ```bash
    pip install PySide6 opencv-python numpy pillow qrcode python-barcode pyzbar
    ```

    *Note: For `pyzbar` to work correctly on Windows, you might need the [Visual C++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170).*

## Usage

1.  Run the main application:

    ```bash
    python ui_app.py
    ```

    *Note: `main.py` is a simpler, command-line based version of the scanner.* - Wait, `main.py` is a minimal GUI using cv2.imshow, not strictly command-line.

2.  **Dashboard**: Upon launch, you'll see a dashboard with various options:
    - **Add Code**: Register a new code to the authorized list.
    - **Authenticate**: Switch to authentication mode to verify scans.
    - **Logs**: View history of authorized and unauthorized scans.
    - **Scanner**: Use as a general-purpose scanner.
    - **Generators**: Create new QR codes or barcodes and save them as images.

## Project Structure

- `ui_app.py`: Main entry point for the GUI application.
- `main.py`: Specific lightweight scanner implementation using OpenCV windows.
- `utils.py`: Helper functions for camera initialization and decoding.
- `styles.py`: UI styling constants and helper functions.
- `myDataFile.txt`: Database of authorized codes.
- `Authorized_log.txt`: Log of successful authentications.
- `Unauthorized_log.txt`: Log of failed authentication attempts.

## Troubleshooting

- **Camera not detected**: Ensure your webcam is connected and not being used by another application.
- **Import Errors**: Make sure all dependencies are installed via `pip`.
- **Sound issues**: This app uses `winsound`, which is available only on Windows.
