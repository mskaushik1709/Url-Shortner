document.getElementById("shorten-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const url = document.getElementById("url").value;
    const custom_short_url = document.getElementById("custom_short_url").value;
    const expiration_days = document.getElementById("expiration_days").value;

    const response = await fetch("/shorten", {
        method: "POST",
        headers: {
            "Content-Type": "application/x-www-form-urlencoded",
        },
        body: `url=${encodeURIComponent(url)}&custom_short_url=${encodeURIComponent(custom_short_url)}&expiration_days=${encodeURIComponent(expiration_days)}`,
    });

    const data = await response.json();
    document.getElementById("result").innerText = `Short URL: ${data.short_url}`;
});




// document.getElementById("shorten-form").addEventListener("submit", async (e) => {
//     e.preventDefault();
//     const url = document.getElementById("url").value;
//     const expiration_days = document.getElementById("expiration_days").value;

//     const response = await fetch("/shorten", {
//         method: "POST",
//         headers: {
//             "Content-Type": "application/x-www-form-urlencoded",
//         },
//         body: `url=${encodeURIComponent(url)}&expiration_days=${encodeURIComponent(expiration_days)}`,
//     });

//     const data = await response.json();
//     document.getElementById("result").innerText = `Short URL: ${data.short_url}`;
// });