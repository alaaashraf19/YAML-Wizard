const form = document.getElementById('form');

form.addEventListener('submit', function(e) {
    e.preventDefault();
    const username = document.getElementById('username').value.trim();
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value.trim();
    const confirmPassword = document.getElementById('confirmPassword').value.trim();

    if (password !== confirmPassword) {
        alert('Passwords do not match!');
        return;
    }
    
    try{
        const response = await fetch('http://127.0.0.1:8000/auth/signup', {
            method: 'POST',
            headers: {  'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password })
        });
        if(response.ok){
            const data = await response.json();
            window.location.replace = '/login';
        }
    }
    catch(error){
        console.error('Error:', error);
    }
    
});
