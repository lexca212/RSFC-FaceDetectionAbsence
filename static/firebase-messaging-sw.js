// Import Firebase scripts
importScripts('https://www.gstatic.com/firebasejs/11.8.1/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/11.8.1/firebase-messaging-compat.js');

//Initialize
firebase.initializeApp({
  apiKey: "AIzaSyA0ckDWB1lcYk1lXgqJ5XJrQoR5MkFSr6w",
  authDomain: "asidewamessages.firebaseapp.com",
  projectId: "asidewamessages",
  storageBucket: "asidewamessages.firebasestorage.app",
  messagingSenderId: "246438412870",
  appId: "1:246438412870:web:1fa75e1944e69657a08047",
  measurementId: "G-5LH2F28K1V"
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {
  const title =
    payload.notification?.title || payload.data?.title || 'Notification';

  const options = {
    body: payload.notification?.body || payload.data?.body || '',
    icon: payload.notification?.icon || payload.data?.icon || '/static/assets/images/rsfc_logoyy.png',
    image: payload.notification?.image || payload.data?.image,
    data: {
      url: payload.data?.url || '/'
    }
  };

  self.registration.showNotification(title, options);
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  const url = event.notification.data.url;

  event.waitUntil(
    clients.openWindow(url)
  );
});