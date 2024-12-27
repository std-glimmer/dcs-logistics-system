# README.md Content
# DCS World Logistics System

This project is a logistics management system designed for DCS World, focusing on the management of nodes, supplies, and transport vehicles. The system includes classes for handling logistics operations, logging, and UDP communication.

## Features

- **Node Management**: Represents logistics nodes such as airbases, FOBs, and COPs.
- **Supply Management**: Handles supply deliveries and schedules.
- **Transport Management**: Manages transport vehicles and their capacities.
- **Logging**: Provides logging services for tracking operations.
- **UDP Communication**: Facilitates communication with DCS World.

## Directory Structure

- `src/models`: Contains classes for nodes, supplies, and transport.
- `src/services`: Includes services for logging and UDP communication.
- `src/controllers`: Manages the overall logistics system.
- `src/utils`: Utility functions for JSON handling.
- `src/config`: Configuration settings for the application.
- `src/main.py`: Entry point for the application.
- `data`: Contains JSON files for deliveries, structure, and transport data.
- `logs`: Directory for log files.
- `tests`: Unit tests for models and services.

## Installation

1. Clone the repository.
2. Install the required dependencies using `pip install -r requirements.txt`.

## Usage

Run the application using the command:

```
python src/main.py
```

## License

This project is licensed under the MIT License.