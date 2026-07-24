const hamburger = document.getElementById('navHamburger');
const navLinks = document.getElementById('navLinks');
const navbar = document.querySelector('.navbar');

const toggleNavbarBackground = () => {
    if (!navbar) return;
    if (window.scrollY > 20) {
        navbar.classList.add('scrolled');
    } else {
        navbar.classList.remove('scrolled');
    }
};

window.addEventListener('scroll', toggleNavbarBackground);
window.addEventListener('load', toggleNavbarBackground);

hamburger.addEventListener('click', () => {
    hamburger.classList.toggle('active');
    navLinks.classList.toggle('active');
});

navLinks.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => {
        hamburger.classList.remove('active');
        navLinks.classList.remove('active');
    });
});
