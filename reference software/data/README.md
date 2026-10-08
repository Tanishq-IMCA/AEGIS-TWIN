IMCA Nexus Portable Save System
==============================

This directory contains the local persistent data for the IMCA Nexus software.

Architecture:
- profile.json: Stores user profile metadata (Name, Role, Company, Email).
- avatar.txt: Stores the Base64 encoded profile picture for portability.

Portability:
The software reads these files on every boot. To move your data, simply copy the entire 'data' folder to a new IMCA Nexus installation.

Editing:
You can manually edit profile.json to update user information. The software will detect these changes upon the next refresh or boot.

Future Compatibility:
This structure is designed to be easily bundled into a single .imca archive for future export/import capabilities.
