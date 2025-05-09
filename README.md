# Coin Scanner

A comprehensive cryptocurrency analysis and scanning tool with a Python backend and Next.js frontend.

## Project Structure

The project consists of two main components:

- **python-backend**: The core analysis engine built with Python
- **nextjs-coin-analyzer**: The web interface built with Next.js and TypeScript

## Features

- Cryptocurrency market analysis
- Modular analysis architecture
- Telegram bot integration
- Web API for data access
- Modern responsive UI with Next.js

## Getting Started

### Backend Setup

1. Navigate to the backend directory:
   ```
   cd python-backend
   ```

2. Create a virtual environment:
   ```
   python -m venv .venv
   ```

3. Activate the virtual environment:
   - Windows: `.venv\Scripts\activate`
   - Linux/Mac: `source .venv/bin/activate`

4. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

5. Configure environment variables:
   ```
   cp .env.example .env
   ```
   Then edit the `.env` file with your specific configuration.

6. Run the backend:
   ```
   python main.py
   ```
   
   Or for the modular version:
   ```
   python modular_main.py
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```
   cd nextjs-coin-analyzer
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Configure environment variables:
   ```
   cp .env.example .env.local
   ```
   Then edit the `.env.local` file with your specific configuration.

4. Start the development server:
   ```
   npm run dev
   ```

## Deployment

The project can be deployed using various methods:

- Self-hosted on a VPS
- Docker containers
- Cloud services (AWS, Azure, Google Cloud)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributors

- Add your name here

## Acknowledgments

- Thanks to all the open-source libraries and frameworks that made this project possible. 