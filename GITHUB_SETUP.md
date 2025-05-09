# GitHub Setup Instructions

## 1. Create a Repository on GitHub
1. Go to https://github.com/new
2. Enter "coin-scanner" as the repository name
3. Add a description (optional)
4. Choose whether to make it public or private
5. Do NOT initialize with README, .gitignore, or license (as we already have those)
6. Click "Create repository"

## 2. Connect Your Local Repository
After creating the repository on GitHub, run these commands in your terminal:

```
git remote add origin https://github.com/YOUR_USERNAME/coin-scanner.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your actual GitHub username.

## 3. Authentication
- If you haven't set up authentication, GitHub may prompt you for your username and password
- For security, GitHub no longer accepts regular passwords for command-line operations
- You'll need to use a personal access token instead of a password:
  1. Go to GitHub → Settings → Developer settings → Personal access tokens → Generate new token
  2. Select the required scopes (at minimum: `repo`)
  3. Generate the token and copy it
  4. Use this token as your password when prompted

## 4. Verify Repository Setup
After pushing, refresh your GitHub repository page to confirm your code is now available online. 