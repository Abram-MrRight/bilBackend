document.addEventListener("DOMContentLoaded", function () {
    const typeSelect = document.getElementById("typeSelect");
    const titleSelect = document.getElementById("titleField");
    const iconSelect = document.getElementById("iconField");
    const contentField = document.getElementById("contentField");
    const logoWrapper = document.getElementById("logoWrapper");
    const logoField = document.getElementById("logoField");

    const map = {
        about: { title: "about", icon: "info_outline", placeholder: "Write something about the company..." },
        phone: { title: "phone", icon: "phone", placeholder: "Company phone number..." },
        email: { title: "email", icon: "email", placeholder: "Official company email..." },
        address: { title: "address", icon: "location_on", placeholder: "Company physical address..." },
        logo: { title: "logo", icon: "logo", placeholder: "Name of the Company" }
    };

    function updateFields() {
        const type = typeSelect.value;
        const config = map[type];
        if (!config) return;

        titleSelect.value = config.title;
        iconSelect.value = config.icon;
        contentField.placeholder = config.placeholder;

        if (type === "logo") {
            logoWrapper.style.display = "block";
        } else {
            logoWrapper.style.display = "none";
            logoField.value = "";
        }
    }

    updateFields();
    typeSelect.addEventListener("change", updateFields);
});
