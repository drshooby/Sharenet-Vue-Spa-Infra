# Sharenet Vue SPA Infrastructure

Sharenet Vue SPA is a responsive single-page application built with Vue.js. The project integrates a frontend, backend, and database to display spot prices, workshop details, and contact information. Users can sort data, filter available workshops, and book events. The backend is powered by Node.js, and MySQL is used for data storage.

---

## Features

### For a full list of features, visit the source directory (also check out the original author's code!): 
<a href="https://github.com/drshooby/Sharenet-Vue-Spa">Source<a>  
<a href="https://github.com/MuneerMiller/Sharenet-Vue-Spa">Original by MuneerMiller<a>

## Flow

- **Source** repository sends a dispatch event to this repo to establish the source code on the GitHub Actions Runner.
- A temporary **EC2** instance is spun up to perform basic smoke tests to ensure functionality and cloud compatibility.
- Upon success, the newest iteration of the code is built (frontend and backend images), tagged with **nightly + timestamp** and **latest**, then pushed to an **ECR** registry.
- Every day at 12am PST, the latest images of the frontend and backend are pulled and started up on another **EC2** instance with nginx for routing.
- The data is stored via an **RDS** MySQL instance.
- Additionally, AWS Route 53 handles network records that allow site usage.
