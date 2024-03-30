$(document).ready(function () {
    $('.like-btn').click(function (e) {
        e.preventDefault();
        handleButtonClick($(this), true);
    });

    $('.dislike-btn').click(function (e) {
        e.preventDefault();
        handleButtonClick($(this), false);
    });

    function handleButtonClick(button, isLike) {
        var newsId = button.data('id');
        var url = isLike ? '/like_news/' : '/dislike_news/';
        var otherButton = isLike ? $('.dislike-btn[data-id="' + newsId + '"]') : $('.like-btn[data-id="' + newsId + '"]');

        $.post(url + newsId, function (data) {
            switch (data.result) {
                case 'liked':
                case 'unliked':
                case 'switched_to_like':
                    button.toggleClass('liked');
                    otherButton.removeClass('disliked');
                    break;
                case 'disliked':
                case 'undisliked':
                case 'switched_to_dislike':
                    button.toggleClass('disliked');
                    otherButton.removeClass('liked');
                    break;
            }
        }).fail(function () {
            alert("Error processing your request");
        });
    }
});

$(document).ready(function() {
    $('.read-more-button').click(function() {
        var url = $(this).data('url');
        window.open(url, '_blank');
    });
});

$(document).ready(function() {
    $('.home-button').click(function() {
        window.location.href = '/login';
    });
});


