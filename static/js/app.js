document.addEventListener("DOMContentLoaded", () => {
    const categoryInputs = document.querySelectorAll(
        'input[name="category_id"]'
    );

    const subcategorySection =
        document.getElementById("subcategorySection");

    const subcategoryOptions =
        document.querySelectorAll(".subcategory-option");

    const description =
        document.getElementById("description");

    const characterCount =
        document.getElementById("characterCount");


    /*
     * Category → Subcategory filtering
     */
    categoryInputs.forEach((input) => {

        input.addEventListener("change", () => {

            const selectedCategory =
                input.value;

            let visibleCount = 0;

            subcategoryOptions.forEach((option) => {

                const matches =
                    option.dataset.categoryId ===
                    selectedCategory;

                option.style.display =
                    matches ? "flex" : "none";

                const radio =
                    option.querySelector(
                        'input[type="radio"]'
                    );

                if (!matches) {
                    radio.checked = false;
                }

                if (matches) {
                    visibleCount += 1;
                }
            });


            if (visibleCount > 0) {
                subcategorySection
                    .classList
                    .remove("hidden-section");
            } else {
                subcategorySection
                    .classList
                    .add("hidden-section");
            }
        });
    });


    /*
     * Character counter
     */
    if (description && characterCount) {

        description.addEventListener(
            "input",
            () => {
                characterCount.textContent =
                    `${description.value.length} / 1000`;
            }
        );
    }
});