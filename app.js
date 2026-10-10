// Confirmacions i petits ajuts de la web.
// Es posa en un fitxer propi (i no dins l'HTML) perquè la política de seguretat (CSP) no permet JavaScript inline.

// Qualsevol formulari amb data-confirm="..." demana confirmació abans d'enviar-se
document.addEventListener("submit", function (e) {
    var missatge = e.target.getAttribute("data-confirm");
    if (missatge && !window.confirm(missatge)) {
        e.preventDefault();
    }
});

// Al xat, baixem automàticament fins al missatge més recent
document.addEventListener("DOMContentLoaded", function () {
    var caixaXat = document.getElementById("pantallaXat");
    if (caixaXat) {
        caixaXat.scrollTop = caixaXat.scrollHeight;
    }
});