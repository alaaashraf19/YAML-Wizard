// debug-watch.js
// Run this before npm run dev
console.log('Before npm run dev:', process.env.VITE_API_URL);
const { exec } = require('child_process');

// Monitor environment changes
const watch = setInterval(() => {
  console.log('Current VITE_API_URL:', process.env.VITE_API_URL);
}, 1000);

// Run npm dev
const child = exec('npm run dev');
child.stdout.on('data', (data) => console.log('stdout:', data));
child.stderr.on('data', (data) => console.log('stderr:', data));

// To remove item: Remove-Item Env:VITE_API_URL