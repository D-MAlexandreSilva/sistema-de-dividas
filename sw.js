
self.addEventListener("install", (event) => {
    self.skipWaiting();
});

self.addEventListener("activate", (event) => {
    event.waitUntil(self.clients.claim());
});

self.addEventListener("push", (event) => {
    let dados = {
        title: "Xandão Finance",
        body: "Você tem uma nova notificação!"
    };

    if (event.data) {
        try {
            dados = event.data.json();
        } catch (erro) {
            dados.body = event.data.text();
        }
    }

    event.waitUntil(
        self.registration.showNotification(dados.title, {
             body: dados.body,
             icon: "/static/img/icon-192.png",
            badge: "/static/img/badge-96.png"
        })
    );
});

self.addEventListener("notificationclick", (event) => {
    event.notification.close();

    event.waitUntil(
        self.clients.matchAll({
            type: "window",
            includeUncontrolled: true
        }).then((clientes) => {
            if (clientes.length > 0) {
                return clientes[0].focus();
            }

            return self.clients.openWindow("/");
        })
    );
});
