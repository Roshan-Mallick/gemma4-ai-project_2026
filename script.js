var hamburger = document.getElementById('navHamburger');
var navLinks = document.getElementById('navLinks');
var navbar = document.querySelector('.navbar');

function toggleNavbarBackground() {
    if (!navbar) return;
    if (window.scrollY > 20) {
        navbar.classList.add('scrolled');
    } else {
        navbar.classList.remove('scrolled');
    }
}

window.addEventListener('scroll', toggleNavbarBackground);
window.addEventListener('load', toggleNavbarBackground);

if (hamburger && navLinks) {
    hamburger.addEventListener('click', function () {
        hamburger.classList.toggle('active');
        navLinks.classList.toggle('active');
    });

    navLinks.querySelectorAll('a').forEach(function (link) {
        link.addEventListener('click', function () {
            hamburger.classList.remove('active');
            navLinks.classList.remove('active');
        });
    });
}
